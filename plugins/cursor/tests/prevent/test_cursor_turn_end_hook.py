"""Cursor adapter tests for turn_end_hook — tests JSON format only."""
import json
import pytest
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(stop_hook_active=False):
    return json.dumps({
        "conversation_id": "test_conv",
        "hook_event_name": "stop",
        "stop_hook_active": stop_hook_active,
    })


class TestTurnEndHookCursorAdapter:
    def test_block_output_format(self, capsys):
        """Block result should produce Cursor followup_message format."""
        block_result = HookOutput(action="block", reason="Validate changes?")
        with patch("turn_end_hook.evaluate_turn_end", return_value=block_result), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from turn_end_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["followup_message"] == "Validate changes?"

    def test_noop_output_silent(self, capsys):
        """Noop result should produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("turn_end_hook.evaluate_turn_end", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from turn_end_hook import main
            main()
        assert capsys.readouterr().out == ""
