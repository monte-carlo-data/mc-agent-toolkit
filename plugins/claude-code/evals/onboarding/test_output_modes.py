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
            "MCD_API_ENDPOINT": "https://api.example.invalid",
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
        self.assertIn("secret_access: The agent cannot read the secret.", output)
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


class NoHardcodedEndpointTests(unittest.TestCase):
    """The endpoint decides which Monte Carlo environment is called, and an API key only works
    in its own environment. A hard-coded prod URL sends a dev (or other instance's) key to the
    wrong API, which refuses it (scenario S3). The examples must take it from the profile or a
    required input instead."""

    OUTPUT_MODES = (ROOT / "skills/onboarding/reference/output-modes.md").read_text()

    def test_python_example_reads_endpoint_from_environment(self):
        self.assertNotIn("api.getmontecarlo.com", EXAMPLE)
        self.assertIn('os.environ["MCD_API_ENDPOINT"]', EXAMPLE)

    def test_terraform_provider_blocks_do_not_hardcode_endpoint(self):
        blocks = [b.split("```", 1)[0] for b in self.OUTPUT_MODES.split("```hcl\n")[1:]]
        provider_blocks = [b for b in blocks if 'provider "montecarlo"' in b]
        self.assertTrue(provider_blocks, "expected a montecarlo provider block")
        for block in provider_blocks:
            self.assertNotRegex(block, r'endpoint\s*=\s*"https?://')


class TerraformVersionFloorTests(unittest.TestCase):
    """Every Terraform artifact uses one version floor, so a customer never gets a block that
    can't take the write-only secrets another step needs (scenario S6 wrote `>= 1.5` for the
    data store's AWS-only Terraform). The rule must reach AWS-only artifacts too."""

    SKILL = (ROOT / "skills/onboarding/SKILL.md").read_text()
    OUTPUT_MODES = (ROOT / "skills/onboarding/reference/output-modes.md").read_text()

    def test_every_terraform_settings_block_requires_1_11(self):
        blocks = [b.split("```", 1)[0] for b in self.OUTPUT_MODES.split("```hcl\n")[1:]]
        settings = [b for b in blocks if "terraform {" in b]
        self.assertTrue(settings, "expected a terraform settings block")
        for block in settings:
            self.assertIn('required_version = ">= 1.11"', block)

    def test_floor_applies_to_aws_only_artifacts(self):
        self.assertIn("including one with only AWS resources", self.SKILL)


class DeleteProvenanceTests(unittest.TestCase):
    """Monte Carlo doesn't record which tool created a resource. Deleting a Terraform-managed one
    through MCP leaves the state pointing at nothing, and the next apply recreates it (scenario
    S6 offered MCP deletes for a connection Terraform created in S4). The skill must ask first and
    hand Terraform-managed resources back to Terraform, with a check that prints no state."""

    SKILL = (ROOT / "skills/onboarding/SKILL.md").read_text()
    OUTPUT_MODES = (ROOT / "skills/onboarding/reference/output-modes.md").read_text()

    def test_skill_asks_how_an_existing_resource_was_created(self):
        self.assertIn("Ask how an existing resource was created before deleting it", self.SKILL)

    def test_output_modes_has_terraform_removal_steps(self):
        self.assertIn("### Remove what Terraform manages", self.OUTPUT_MODES)

    def section(self):
        return self.OUTPUT_MODES.split("### Remove what Terraform manages", 1)[-1].split("\n## ", 1)[0]

    def test_state_check_matches_resource_ids_without_printing_state(self):
        # A whole-state grep also matches reused resources whose ids appear as references on
        # managed ones, and an empty -id lists every resource, so the check is guarded.
        section = self.section()
        self.assertIn('[ -n "${ID}" ] && terraform state list -id="${ID}"', section)
        self.assertNotIn("state pull", section)
        self.assertNotIn("terraform show", section)

    def test_terraform_addresses_are_quoted(self):
        # Addresses can carry [0] or ["key"]; unquoted, zsh globs them before Terraform runs.
        section = self.section()
        self.assertIn("terraform destroy -target='<address>'", section)
        self.assertIn("terraform state rm '<address>'", section)


class ModelComparisonFindingsTests(unittest.TestCase):
    """Findings from running the onboarding scenarios across models (2026-10-01): each rule
    below closed a gap one of the models fell into."""

    # Whitespace collapsed, so rewrapping the prose doesn't break the checks.
    SKILL = " ".join((ROOT / "skills/onboarding/SKILL.md").read_text().split())
    OUTPUT_MODES = " ".join((ROOT / "skills/onboarding/reference/output-modes.md").read_text().split())
    TROUBLESHOOTING = " ".join((ROOT / "skills/onboarding/reference/troubleshooting.md").read_text().split())
    CONNECTION_INPUTS = " ".join((ROOT / "skills/onboarding/reference/connection-inputs.md").read_text().split())

    def test_credentials_pass_does_not_rule_out_iam(self):
        # Right after a successful read the agent keeps the secret, so a fresh IAM break shows
        # "credentials passed" with no warning; one model took that as a network problem.
        self.assertIn("A credentials pass doesn't prove the agent can read the secret now", self.TROUBLESHOOTING)
        self.assertIn("credentials valid with no warning, after a recent", self.TROUBLESHOOTING)

    def test_policy_edits_use_the_normalised_diff(self):
        # AWS CLI JSON (4 spaces) vs jq (2 spaces) makes a raw diff mark every line.
        self.assertIn("diff <(jq -S . backup.json) <(jq -S . new.json)", self.TROUBLESHOOTING)

    def test_single_arn_simulator_uses_the_same_query(self):
        self.assertIn("Use the same query for a single ARN", self.OUTPUT_MODES)
        self.assertIn("EvalResourceDecision` exists only per resource", self.OUTPUT_MODES)

    def test_grant_handover_uses_the_reference_commands(self):
        # A model that never opened output-modes improvised the grant without its guards.
        self.assertIn("read that section and hand over its commands", self.SKILL)

    def test_pasted_secret_is_never_repeated(self):
        # One model echoed the pasted password while asking the user to rotate it.
        self.assertIn("never repeat or quote it, not even to ask for rotation", self.SKILL)

    def test_revoking_one_secret_checks_scope_first(self):
        section = self.OUTPUT_MODES.split("### Revoke the agent's access to one secret", 1)
        self.assertEqual(len(section), 2, "expected a revoke section")
        body = section[1].split(" ### ", 1)[0]
        self.assertIn("get-role-policy", body)
        self.assertIn("delete-role-policy", body)
        self.assertIn("implicitDeny", body)


class BiConnectionTests(unittest.TestCase):
    """Tableau, Looker and Power BI connect through a BI container, not a warehouse."""

    SKILL = ModelComparisonFindingsTests.SKILL
    OUTPUT_MODES = ModelComparisonFindingsTests.OUTPUT_MODES
    CONNECTION_INPUTS = ModelComparisonFindingsTests.CONNECTION_INPUTS

    def test_bi_connections_go_on_a_bi_container(self):
        self.assertIn("`list_bi_containers`", self.SKILL)
        self.assertIn("`create_bi_container`", self.SKILL)
        self.assertIn("create_connection(name, bi_container_id, credentials_id)", self.SKILL)
        self.assertIn("NEVER create a warehouse for a BI tool", self.CONNECTION_INPUTS)
        self.assertNotIn("connected in the UI", self.CONNECTION_INPUTS)

    def test_one_looker_container_holds_both_looker_connections(self):
        self.assertIn("one `looker` container holds both", self.SKILL)

    def test_bi_credential_inputs_are_listed_per_type(self):
        for heading in ("#### Tableau", "#### Looker API", "#### Looker git clone", "#### Power BI"):
            self.assertIn(heading, self.CONNECTION_INPUTS)
        # Tableau's three sign-in methods are exclusive; sending two is refused.
        self.assertIn("exactly one sign-in method", self.CONNECTION_INPUTS)

    def test_bi_secrets_are_write_only_in_terraform_and_never_literal_in_the_cli(self):
        self.assertIn('resource "montecarlo_bi_container"', self.OUTPUT_MODES)
        self.assertIn("password_wo", self.OUTPUT_MODES)
        self.assertIn("bi_container_id = montecarlo_bi_container.", self.OUTPUT_MODES)
        self.assertIn("montecarlo credentials create tableau", self.OUTPUT_MODES)
        self.assertIn("--password-prompt", self.OUTPUT_MODES)
