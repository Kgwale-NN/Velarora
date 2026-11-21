"""Read-only demonstration checks; optional private SQLite/settings backup."""
import argparse
import importlib.metadata
import shutil
import socket
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup", action="store_true")
    args = parser.parse_args()
    missing = []

    def check(label, ready):
        print(("OK   " if ready else "CHECK ") + label)
        if not ready:
            missing.append(label)

    for label, relative in [("React build", "frontend/react/dist/index.html"),
                            ("Private environment", ".env"),
                            ("Existing database", "data/monitor.db"),
                            ("Windows workstation agent", "workstation/agent.py")]:
        check(label, (ROOT / relative).is_file())
    check("Veyon installed", Path(r"C:\Program Files\Veyon\veyon-cli.exe").is_file())
    for package in ("nicegui", "torch", "onnxruntime", "psutil"):
        try:
            version = importlib.metadata.version(package)
            check(package + " " + version, True)
        except importlib.metadata.PackageNotFoundError:
            check(package, False)
    for port, name in [(8080, "Velarora running on port 8080"),
                       (11080, "Veyon WebAPI running on port 11080")]:
        with socket.socket() as client:
            client.settimeout(2)
            check(name, client.connect_ex(("127.0.0.1", port)) == 0)
    database = ROOT / "data/monitor.db"
    if database.exists():
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as source:
            models = source.execute("SELECT onnx_path, pt_path FROM ml_model WHERE is_active=1").fetchall()
            paths = [Path(row[0] or row[1] or "") for row in models]
            check("Active trained model file", bool(paths) and all(
                (path if path.is_absolute() else ROOT / path).is_file() for path in paths))
            if args.backup:
                target = ROOT / "data/demo/backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                if shutil.disk_usage(ROOT).free < database.stat().st_size * 2 + 104857600:
                    raise SystemExit("Not enough free space for a private backup.")
                target.mkdir(parents=True)
                with sqlite3.connect(target / "monitor.db") as destination:
                    source.backup(destination)
                for name in (".env", ".nicegui"):
                    item = ROOT / name
                    if item.is_dir():
                        shutil.copytree(item, target / name)
                    elif item.is_file():
                        shutil.copy2(item, target / name)
                (target / "README.txt").write_text(
                    "Private database and settings backup. Keep offline. "
                    "Model files remain in the original project; this is not a full portable archive.",
                    encoding="utf-8")
                print("Private database/settings backup: " + str(target))
    print("No secrets or student records were displayed.")
    if missing:
        raise SystemExit("Resolve the CHECK items before your demonstration.")
    print("Local demo prerequisites passed. Verify capture and sound on the actual demo PC.")


if __name__ == "__main__":
    main()
