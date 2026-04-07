"""CC adapter tests for post_edit_hook — tests JSON format only."""
import json
import pytest
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(file_path):
    return json.dumps({
        "session_id": "test_session",
        "tool_input": {"file_path": file_path},
    })


class TestPostEditHookCCAdapter:
    def test_silent_output(self, capsys):
        """Post-edit hook should always produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("post_edit_hook.evaluate_post_edit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from post_edit_hook import main
            main()
        assert capsys.readouterr().out == ""
