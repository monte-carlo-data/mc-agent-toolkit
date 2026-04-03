"""CC adapter tests for validate_command — tests JSON format only."""
import json
import pytest
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin():
    return json.dumps({
        "session_id": "test_session",
    })


class TestValidateCommandCCAdapter:
    def test_context_output_format(self, capsys):
        """Context result should produce CC additionalContext format."""
        ctx_result = HookOutput(action="context", context="Generate queries for: orders.")
        with patch("validate_command.evaluate_validate_command", return_value=ctx_result), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from validate_command import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert "orders" in output["hookSpecificOutput"]["additionalContext"]
