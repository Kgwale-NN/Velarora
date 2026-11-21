# Demonstrating Velarora on a Windows PC

## Use this PC as the server

Keep Velarora, Veyon and the workstation agent running on the Windows PC used for the demo. The browser can be on that PC or on a classroom big screen. A public website alone cannot read another PC's foreground apps or play its Windows alarm.

From the project folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Monitor.ps1
```

Open http://127.0.0.1:8080. In a second terminal:

```powershell
.\.venv\Scripts\python.exe .\scripts\Check-Demo.py --backup
```

The check displays no secrets. Its optional backup uses SQLite's online backup API, including committed screenshots stored in the database, and copies the private .env and .nicegui settings. It does not copy model binaries; keep the original project too. Backups stay under ignored data/demo/backups and must not be uploaded to GitHub.

## Moving to a different PC

Use Windows and follow LOCAL-SETUP.md to recreate Python and Node dependencies. Do not copy .venv or node_modules as a portable installation. GitHub does not contain your private database, trained models, Veyon keys, .env or .nicegui settings. Transfer those privately when needed. Model paths and Veyon key paths may need updating if the project folder changes. Veyon credentials in Windows Credential Manager must be configured on the new Windows account. Select the correct PC in Classrooms and configure its own agent; do not reuse one agent identity for different PCs.

## Optional temporary public HTTPS link

A Cloudflare Quick Tunnel can forward this PC's running port 8080 to a temporary HTTPS address. Publishing is not enabled automatically. It makes the login page reachable from the internet and forwards traffic through Cloudflare; authenticated users can access the records and controls their roles permit. Public sharing requires explicit approval before starting the tunnel. The demo URL changes when the tunnel restarts, and it stops when the PC, app, tunnel or internet connection stops. This is a demonstration arrangement, not always-on hosting.

The existing Google callback is configured for the local address. Google sign-in on a different public address requires the exact HTTPS callback URL to be registered in Google Cloud and configured in Velarora. Password sign-in remains the normal demonstration option until that setup is verified. Existing workstation agents can keep using their working local configuration for a same-PC demo; agents using a public address need the current address and their own token configuration.

## Demonstration acceptance

1. Sign in as admin and as teacher and check that their access remains different.
2. Select the local-test classroom and the intended active model.
3. Start an exam and check that a current screenshot appears.
4. Open a deliberately blocked app on the demo PC; check the PC name and app notification.
5. Hear the continuous alarm, then use the owning teacher's Stop alarm and confirm silence.
6. Run a short schedule and verify start/end. An outstanding alarm still requires its stop command.
7. View history, analytics and a downloaded report.

A successful web request does not prove screen capture, physical audio or Google login. Perform these checks on each Windows PC you intend to present from, preferably before demonstration day. See CLASSROOM-SETUP.md for the agent setup.


## Start and stop an approved public demo link

After starting Velarora, run the following in a second terminal. This publishes the app through Cloudflare and displays its temporary HTTPS URL. The script verifies the official tunnel executable checksum when installing, reuses an already running link, and never starts a second Velarora server.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Demo-Link.ps1
```

To remove public access while keeping Velarora running locally:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Demo-Link.ps1 -Action Stop
```

The stop action checks the saved process start time and executable before stopping it. Private process details, download metadata and URLs stay under ignored data folders. `OPEN_BROWSER=false` can be set in the server process environment for background startup without changing .env. HTTPS responses mark session cookies Secure while local HTTP behaviour remains supported.
