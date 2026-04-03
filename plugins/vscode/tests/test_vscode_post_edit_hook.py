"""VS Code adapter tests for post_edit_hook — tests JSON format only."""
import json
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(file_path):
    return json.dumps({
        "sessionId": "test_session",
        "hookEventName": "PostToolUse",
        "tool_name": "editFiles",
        "tool_input": {"filePath": file_path},
    })


class TestPostEditHookVSCodeAdapter:
    def test_silent_output(self, capsys):
        """Post-edit hook should always produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("post_edit_hook.evaluate_post_edit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from post_edit_hook import main
            main()
        assert capsys.readouterr().out == ""

    def test_file_path_in_tool_input(self):
        """VS Code PostToolUse provides filePath inside tool_input."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert raw["tool_input"]["filePath"] == "/project/models/orders.sql"
