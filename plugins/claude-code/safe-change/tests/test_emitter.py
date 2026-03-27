import json
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

from lib.emitter import _get_git_identity


class TestGetGitIdentity:
    def test_returns_email_and_name(self):
        with patch("lib.emitter.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="alice@company.com\n", returncode=0),
                MagicMock(stdout="Alice Chen\n", returncode=0),
            ]
            result = _get_git_identity()
        assert result == {"git_email": "alice@company.com", "git_name": "Alice Chen"}

    def test_returns_empty_on_failure(self):
        with patch("lib.emitter.subprocess.run", side_effect=Exception("no git")):
            result = _get_git_identity()
        assert result == {"git_email": "", "git_name": ""}
