"""Exercise fresh cloud startup without Windows capture or training dependencies."""
import os
from pathlib import Path
import subprocess
import sys


def test_cloud_starts_without_torch_ultralytics_or_opencv(tmp_path):
    root = Path(__file__).resolve().parents[2]
    code = '''
import importlib.abc
import sys
class NoDesktopML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.split('.')[0] in {'torch', 'ultralytics', 'cv2'}:
            raise AssertionError('Cloud startup loaded desktop dependency: ' + fullname)
sys.meta_path.insert(0, NoDesktopML())
import dotenv
dotenv.load_dotenv = lambda *a, **k: None
from nicegui import ui, app
ui.run = lambda **kwargs: None
app.on_startup = lambda handler: handler
import backend.main as main
main._startup()
from backend.db._core import _conn
assert _conn().execute('SELECT COUNT(*) FROM user').fetchone()[0] == 1
assert main.BIND_PORT == 12345
assert main.healthz() == {'status': 'ok'}
assert not any(name in sys.modules for name in ('torch','ultralytics','cv2'))
print('cloud startup passed')
'''
    environment = {
        **os.environ,
        "PYTHONPATH": str(root),
        "VELARORA_CLOUD_DEMO": "true",
        "STORAGE_SECRET": "isolated-test-secret-never-used-in-production",
        "INITIAL_ADMIN_EMAIL": "cloud-test@example.invalid",
        "INITIAL_ADMIN_USERNAME": "Cloud Test",
        "INITIAL_ADMIN_PASSWORD": "CloudTestPassword123!",
        "NICEGUI_STORAGE_PATH": str(tmp_path / ".nicegui"),
        "PORT": "12345",
        "OPEN_BROWSER": "false",
    }
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=environment,
        capture_output=True, text=True, timeout=45,
    )
    assert result.returncode == 0, result.stderr
    assert "cloud startup passed" in result.stdout
