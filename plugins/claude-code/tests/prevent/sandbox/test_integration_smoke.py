"""End-to-end smoke: simulate the Workflow 6/7 script chain on the happy path."""
import json
import subprocess
import sys
from pathlib import Path


SANDBOX_DIR = (
    Path(__file__).resolve().parents[3]
    / "skills" / "prevent" / "scripts" / "sandbox"
)

PROFILES = """
default:
  target: prod
  outputs:
    prod:
      type: snowflake
      database: personal_alice
      schema: prod
      role: DATA_ANALYST
      warehouse: research
      account: dka87615.us-east-1
"""

MODEL_SQL = """\
{{ config(materialized='table', schema='prod') }}
SELECT 1 AS account_id
"""

VALIDATION_SQL = """\
-- validation queries
SELECT 'dev' AS src FROM <YOUR_DEV_DATABASE>.prod.client_hub
UNION ALL
SELECT 'prod' AS src FROM analytics.prod.client_hub
WHERE <YOUR_DEV_DATABASE>.prod.client_hub.account_id IS NOT NULL;
"""


def _run(script: str, *args) -> tuple[int, str, str]:
    out = subprocess.run(
        [sys.executable, str(SANDBOX_DIR / script), *args],
        capture_output=True, text=True,
    )
    return out.returncode, out.stdout, out.stderr


def test_happy_path(tmp_path):
    profiles = tmp_path / "profiles.yml"
    profiles.write_text(PROFILES)
    model = tmp_path / "client_hub.sql"
    model.write_text(MODEL_SQL)
    sql = tmp_path / "client_hub_20260423.sql"
    sql.write_text(VALIDATION_SQL)

    # 1. Parse profiles.
    code, out, err = _run("parse_profiles.py", str(profiles))
    assert code == 0, err
    profile_info = json.loads(out)
    assert profile_info["database"] == "personal_alice"

    # 2. Classify.
    code, out, _ = _run("classify_sandbox.py", profile_info["database"])
    assert code == 0
    assert json.loads(out)["classification"] == "personal"

    # 3. No hard-coded database in the model.
    code, out, _ = _run("detect_hardcoded_db.py", str(model))
    assert code == 0
    assert json.loads(out)["database"] is None

    # 4. Substitute placeholders. Default output lives in validation/run/.
    code, out, _ = _run("substitute_placeholders.py", str(sql), "--dev-db", "personal_alice")
    assert code == 0
    sub_info = json.loads(out)
    assert sub_info["replaced_count"] == 2
    assert "analytics" in sub_info["literal_databases"]
    from pathlib import Path as _P
    assert _P(sub_info["output_path"]).parent == sql.parent / "run"

    # 5. Read-only check on the substituted output.
    code, out, _ = _run("readonly_check.py", sub_info["output_path"])
    assert code == 0
    assert json.loads(out)["ok"] is True


def test_prod_classification_gets_flagged(tmp_path):
    # Engineer's profile is mis-pointed at real prod.
    profiles = tmp_path / "profiles.yml"
    profiles.write_text(PROFILES.replace("personal_alice", "ANALYTICS"))
    code, out, _ = _run("parse_profiles.py", str(profiles))
    assert code == 0
    db = json.loads(out)["database"]
    code, out, _ = _run("classify_sandbox.py", db)
    assert json.loads(out)["classification"] == "prod"
