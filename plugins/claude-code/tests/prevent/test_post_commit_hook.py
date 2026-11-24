"""CC adapter tests for post_commit_hook — tests JSON format only."""
import json
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(command="git commit -m 'test'"):
    return json.dumps({
        "session_id": "test_session",
        "cwd": "/project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"stdout": "", "stderr": ""},
    })


class TestPostCommitHookCCAdapter:
    def test_context_output_format(self, capsys):
        """Context result should produce CC PostToolUse additionalContext format."""
        ctx_result = HookOutput(action="context", context="Offer Bayes?")
        with patch("post_commit_hook.evaluate_post_commit", return_value=ctx_result) as evaluate, \
             patch("sys.stdin", StringIO(_make_stdin())):
            from post_commit_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert output["hookSpecificOutput"]["additionalContext"] == "Offer Bayes?"
        inp = evaluate.call_args.args[0]
        assert inp.session_id == "test_session"
        assert inp.command == "git commit -m 'test'"

    def test_noop_output_silent(self, capsys):
        """Noop result should produce no output."""
        with patch("post_commit_hook.evaluate_post_commit", return_value=HookOutput()), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from post_commit_hook import main
            main()
        assert capsys.readouterr().out == ""
