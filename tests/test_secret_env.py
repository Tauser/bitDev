import os
import subprocess
import sys
from pathlib import Path


def _run_import(with_secret: bool):
    repo = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("BITDEV_FLASK_SECRET_KEY", None)
    if with_secret:
        env["BITDEV_FLASK_SECRET_KEY"] = "unit-test-secret"

    return subprocess.run(
        [sys.executable, "-c", "import app; print('ok')"],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
    )


def test_app_import_with_secret_env_succeeds():
    result = _run_import(with_secret=True)
    assert result.returncode == 0
    assert "ok" in result.stdout


def test_app_import_without_secret_env_fails_with_clear_message():
    result = _run_import(with_secret=False)
    assert result.returncode != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "BITDEV_FLASK_SECRET_KEY" in combined
