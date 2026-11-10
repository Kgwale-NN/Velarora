# Run Velarora on Windows

Install Python (64-bit) and open the Velarora folder in VS Code. In a PowerShell terminal run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into STORAGE_SECRET in .env. Choose your own INITIAL_ADMIN_PASSWORD and use BIND_HOST=127.0.0.1 for a local-only dashboard. Keep .env private.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Monitor.ps1
```

Open http://127.0.0.1:8080 and sign in with the initial admin account. Keep the terminal open. Press Ctrl+C to stop.

For monitoring, install and configure Veyon on your Windows computers. Set the server address and authentication key in Settings, then import and activate a compatible model on the Models page. A fresh clone does not include a private key, database, screenshots or trained model. See [upstream documentation](UPSTREAM.md) for connection setup.

Run tests with `.\.venv\Scripts\python.exe -m pytest tests -q`.
