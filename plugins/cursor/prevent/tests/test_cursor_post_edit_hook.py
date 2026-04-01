"""Cursor adapter tests for post_edit_hook — tests JSON format only."""
import json
import pytest
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(file_path):
    return json.dumps({
        "conversation_id": "test_conv",
        "file_path": file_path,
        "hook_event_name": "afterFileEdit",
    })


class TestPostEditHookCursorAdapter:
    def test_silent_output(self, capsys):
        """Post-edit hook should always produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("post_edit_hook.evaluate_post_edit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from post_edit_hook import main
            main()
        assert capsys.readouterr().out == ""

    def test_file_path_from_top_level(self):
        """Cursor afterFileEdit provides file_path at top level, not in tool_input."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert raw["file_path"] == "/project/models/orders.sql"
        assert "tool_input" not in raw
