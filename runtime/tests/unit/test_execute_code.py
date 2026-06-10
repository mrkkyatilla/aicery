import inspect
import os
from unittest.mock import MagicMock, patch

import pytest

from tools.builtins.execute_code import execute_code


def test_execute_code_uses_http_not_subprocess():
    source = inspect.getsource(execute_code)
    assert "import subprocess" not in source
    assert "subprocess.run" not in source
    assert "httpx" in source


def test_execute_code_disabled_by_default():
    with patch.dict(os.environ, {"EXECUTE_CODE_ENABLED": "false"}, clear=False):
        with pytest.raises(RuntimeError, match="disabled"):
            execute_code("print(1)")


def test_execute_code_calls_sidecar():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"stdout": "1\n", "stderr": "", "exit_code": 0}
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp

    env = {"EXECUTE_CODE_ENABLED": "true", "SANDBOX_RUNNER_URL": "http://127.0.0.1:8091"}
    with patch.dict(os.environ, env, clear=False):
        with patch("tools.builtins.execute_code.httpx.Client", return_value=mock_client):
            result = execute_code("print(1)")
    assert result["stdout"].strip() == "1"
    mock_client.post.assert_called_once()
