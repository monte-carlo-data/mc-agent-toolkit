"""Offline behavioral checks for the shipped Python example, without SDK/network writes.

Run: python3 -m unittest discover -s plugins/claude-code/evals/onboarding -p 'test_*.py'
"""
import contextlib
import io
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as Row
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
EXAMPLE = (ROOT / "skills/onboarding/reference/output-modes.md").read_text().split("```python\n", 1)[1].split("\n```", 1)[0]


class ApiError(Exception):
    status = 503


class Backend:
    def __init__(self):
        self.deployments = []
        self.credentials = []
        self.warehouses = []
        self.connections = []
        self.calls = []
        self.enable_on_register = True
        self.validation_passes = True

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append(name)
            if name == "get_current_user":
                return Row(account_id="account", account_name="Test", account_frozen=False)
            if name == "list_deployments":
                return self.deployments
            if name == "get_deployment":
                return next(x for x in self.deployments if x.id == args[0])
            if name == "create_deployment":
                row = Row(**vars(args[0]), id="dep", enabled=False, aws_external_id="external-id")
                self.deployments.append(row)
                return row
            if name == "register_aws_collection_agent":
                self.deployments[0].enabled = self.enable_on_register
                return Row(id="agent")
            if name == "get_aws_secrets_manager_credentials":
                return next(x for x in self.credentials if x.id == args[0])
            if name == "validate_aws_secrets_manager_credentials":
                return Row(id="run", status="running", validations=[])
            if name == "get_validation_run":
                error = Row(friendly_message="The agent cannot read the secret.", resolution="Grant secretsmanager:GetSecretValue.")
                check = Row(name="secret_access", passed=self.validation_passes, errors=[] if self.validation_passes else [error])
                return Row(id=args[0], status="completed", validations=[check])
            if name == "create_aws_secrets_manager_credentials":
                row = Row(**vars(args[0]), id="cred", storage_type="aws_secrets_manager", assumable_role=None)
                self.credentials.append(row)
                return row
            if name == "create_warehouse":
                row = Row(**vars(args[0]), id="warehouse")
                self.warehouses.append(row)
                return row
            if name == "create_connection":
                row = Row(**vars(args[0]), id="connection", connection_type="snowflake", deployment_id="dep")
                self.connections.append(row)
                return row
            if name.startswith("list_"):
                rows = getattr(self, name.removeprefix("list_"))
                if "warehouse_id" in kwargs:
                    rows = [x for x in rows if x.warehouse_id == kwargs["warehouse_id"]]
                return rows
            raise AssertionError(name)
        return call


class ExampleTests(unittest.TestCase):
    def setUp(self):
        self.backend = Backend()
        self.env = {
            "MCD_DEPLOYMENT_NAME": "approved-agent",
            "MCD_WAREHOUSE_NAME": "Snowflake production",
            "MCD_CONNECTION_NAME": "production",
            "SNOWFLAKE_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:snowflake",
        }

    def run_example(self):
        sdk = ModuleType("montecarlo")
        sdk.Options = Row
        sdk.new_client = lambda options: None
        sdk.ApiException = ApiError
        for name in ["UsersApi", "DeploymentsApi", "CollectionAgentsApi", "CredentialsApi", "WarehousesApi", "ConnectionsApi", "ValidationsApi"]:
            setattr(sdk, name, lambda client: self.backend)
        for name in ["DeploymentIn", "AwsCollectionAgentIn", "AwsSecretsManagerCredentialsIn", "AwsSecretsManagerCredentialsValidateIn", "WarehouseIn", "ConnectionIn"]:
            setattr(sdk, name, Row)
        paging = ModuleType("montecarlo.paging")
        paging.paginate = lambda method, **kwargs: iter(method(**kwargs))
        out = io.StringIO()
        with patch.dict(sys.modules, {"montecarlo": sdk, "montecarlo.paging": paging}), patch.dict(os.environ, self.env, clear=True), contextlib.redirect_stdout(out), contextlib.redirect_stderr(out), patch("time.sleep"):
            namespace = {"__name__": "onboarding_example"}
            exec(compile(EXAMPLE, "output-modes.md", "exec"), namespace)
            status = namespace["main"]()
        return status, out.getvalue()

    def existing_deployment(self, enabled=True, name="approved-agent", platform="AWS"):
        self.backend.deployments.append(Row(id="dep", name=name, type="COLLECTION_AGENT", runtime_platform=platform, enabled=enabled, aws_external_id="external-id"))

    def test_no_implicit_new_deployment(self):
        status, _ = self.run_example()
        self.assertEqual(status, 1)
        self.assertIn("list_deployments", self.backend.calls)
        self.assertNotIn("create_deployment", self.backend.calls)

    def test_first_run_stops_for_infrastructure(self):
        self.env["MCD_CREATE_DEPLOYMENT"] = "1"
        status, output = self.run_example()
        self.assertEqual(status, 0)
        self.assertNotIn("register_aws_collection_agent", self.backend.calls)
        self.assertNotIn("create_aws_secrets_manager_credentials", self.backend.calls)
        self.assertIn("MCD_DEPLOYMENT_ID=dep", output)
        self.assertNotIn("Validate connection", output)

    def test_resume_registers_before_credentials(self):
        self.existing_deployment(enabled=False)
        self.env.update(MCD_DEPLOYMENT_ID="dep", LAMBDA_ARN="lambda", ROLE_ARN="role")
        status, _ = self.run_example()
        self.assertEqual(status, 0)
        self.assertLess(self.backend.calls.index("register_aws_collection_agent"), self.backend.calls.index("create_aws_secrets_manager_credentials"))

    def test_credentials_validated_before_create(self):
        self.existing_deployment()
        status, _ = self.run_example()
        self.assertEqual(status, 0)
        calls = self.backend.calls
        self.assertLess(calls.index("validate_aws_secrets_manager_credentials"), calls.index("get_validation_run"))
        self.assertLess(calls.index("get_validation_run"), calls.index("create_aws_secrets_manager_credentials"))

    def test_failed_validation_creates_nothing(self):
        self.existing_deployment()
        self.backend.validation_passes = False
        status, output = self.run_example()
        self.assertEqual(status, 1)
        self.assertNotIn("create_aws_secrets_manager_credentials", self.backend.calls)
        self.assertNotIn("create_warehouse", self.backend.calls)
        self.assertIn("The agent cannot read the secret.", output)
        self.assertIn("Grant secretsmanager:GetSecretValue.", output)

    def test_failed_enable_stops_connection_work(self):
        self.existing_deployment(enabled=False)
        self.backend.enable_on_register = False
        self.env.update(MCD_DEPLOYMENT_ID="dep", LAMBDA_ARN="lambda", ROLE_ARN="role")
        status, _ = self.run_example()
        self.assertEqual(status, 1)
        self.assertNotIn("create_aws_secrets_manager_credentials", self.backend.calls)

    def test_repeat_reuses_all_ids_without_writes(self):
        self.existing_deployment()
        self.assertEqual(self.run_example()[0], 0)
        self.backend.calls.clear()
        status, output = self.run_example()
        self.assertEqual(status, 0)
        self.assertFalse(any(x.startswith(("create_", "register_")) for x in self.backend.calls))
        for resource_id in ["dep", "cred", "warehouse", "connection"]:
            self.assertIn(resource_id, output)

    def test_existing_selected_deployment_does_not_create(self):
        self.existing_deployment(name="another-name")
        self.env["MCD_DEPLOYMENT_ID"] = "dep"
        self.assertEqual(self.run_example()[0], 0)
        self.assertNotIn("create_deployment", self.backend.calls)

    def test_wrong_deployment_platform_stops(self):
        self.existing_deployment(platform="GCP")
        self.assertEqual(self.run_example()[0], 1)
        self.assertNotIn("create_aws_secrets_manager_credentials", self.backend.calls)

    def test_not_first_warehouse_of_same_type(self):
        self.existing_deployment()
        self.backend.warehouses.append(Row(id="unrelated", name="Snowflake development", type="snowflake", deployment_id="dep"))
        self.assertEqual(self.run_example()[0], 0)
        self.assertEqual(self.backend.connections[0].warehouse_id, "warehouse")

    def test_ambiguous_credentials_require_selection(self):
        self.existing_deployment()
        for identifier in ["c1", "c2"]:
            self.backend.credentials.append(Row(id=identifier, connection_type="snowflake", storage_type="aws_secrets_manager", aws_secret=self.env["SNOWFLAKE_SECRET_ARN"], assumable_role=None))
        self.assertEqual(self.run_example()[0], 1)
        self.assertNotIn("create_warehouse", self.backend.calls)

    def test_connection_name_collision_does_not_create(self):
        self.existing_deployment()
        self.backend.warehouses.append(Row(id="warehouse", name=self.env["MCD_WAREHOUSE_NAME"], type="snowflake", deployment_id="dep"))
        self.backend.connections.append(Row(id="other", name="production", warehouse_id="warehouse", credentials_id="other-credential", connection_type="snowflake", deployment_id="dep"))
        self.assertEqual(self.run_example()[0], 1)
        self.assertNotIn("create_connection", self.backend.calls)


if __name__ == "__main__":
    unittest.main()
