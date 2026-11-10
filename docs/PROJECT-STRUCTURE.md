# Velarora folder guide

## Normal code view

```text
Velarora/
  backend/
    core/          Authentication, Veyon connection and image detection
    db/            Database queries and schema
    services/      Monitoring, training, schedules, alerts and reports
    config.py      App settings
    main.py        Server startup
    state.py       Shared monitoring state
  frontend/
    pages/         Each page has its own Python file
    locales/       English and Lithuanian interface text
    assets/        Documentation screenshots
    translate.py   Translation helpers
    icon.ico       Build icon
  tests/unit/      Application checks
  tests/database/  Database tests
  scripts/         Start-Monitor.ps1, build.py, build.bat
  docs/            Guides and original project documentation
  data/            Saved records and local files
  run.py           Python entry point
  pyproject.toml   Dependencies and packaging
  readme.md        Start here
  LICENSE         Original licence
```

## Where to look for a bug

| Problem | Start here |
| --- | --- |
| Sign-in page | frontend/pages/login.py and backend/core/auth.py |
| Dashboard display | frontend/pages/dashboard.py |
| Capturing a screen | backend/core/veyon.py |
| AI recognition | backend/core/yolo.py and backend/services/monitor_service.py |
| Training a model | backend/services/training_service.py |
| Exam times | backend/services/schedule_service.py |
| Alerts | backend/services/alert_service.py |
| Reports | frontend/pages/reports.py and backend/services/report_export.py |
| Saved database records | backend/db/ |
| App fails to start | scripts/Start-Monitor.ps1, run.py and backend/main.py |

## Files hidden in VS Code

The Explorer hides generated folders and supporting configuration to keep the
normal code view small. This does not delete or move their contents.

- .venv: shared Python environment.
- .nicegui, .env: existing sessions, settings and secrets.
- .pytest_cache, .ruff_cache, __pycache__, *.egg-info: generated files.
- weights, runs, root *.pt and *.onnx files: existing models and training output.
  They remain at their original paths because settings and database records can
  refer to them and the app may be running during this cleanup.
- .github, .vscode, .gitignore, .gitattributes, .env.example: project tooling.
- Start-Monitor.ps1: compatibility launcher for the older startup command.

To reveal them, open VS Code Settings, search for **Files: Exclude**, and disable
the relevant entry for this workspace. Windows File Explorer also shows them.
Configuration is stored in .vscode/settings.json.

## Saved local files

- data/monitor.db: accounts, schedules, reports and detections.
- data/logs/: previous server log files.
- Credentials and private login notes belong only on the local computer.
- data/: other existing datasets, model files, keys and runtime logs.

Never publish private data, screenshots, keys or passwords.

## Run and check

Run commands from the Velarora project root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Monitor.ps1
```

Frontend and backend are both Python/NiceGUI and run together. There is no
separate npm frontend. The VS Code task (Ctrl+Shift+B) uses the same script.

```powershell
$env:YOLO_CONFIG_DIR = Join-Path $PWD 'data\ultralytics'
$env:MPLCONFIGDIR = Join-Path $PWD 'data\matplotlib'
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check backend frontend tests scripts run.py
```

Build the Windows executable with `python scripts/build.py` in the activated
environment, or run `scripts\build.bat`. Building requires PyInstaller.

## Small core modules

Every Python file in backend/core has at most 100 lines, including comments
and blank lines. A test checks this limit. Split by responsibility rather
than cutting functions in half.

| Files | Responsibility |
| --- | --- |
| veyon.py | Public imports used by the rest of the app |
| veyon_server.py | Port checks and starting the WebAPI |
| veyon_directory.py | Reading computers and rooms from Veyon |
| veyon_locations.py | Grouping computers into rooms |
| veyon_auth.py | Key and OS-account authentication |
| veyon_capture.py | Screenshots, image decoding and current user |
| tls.py | Checking and reusing certificates |
| tls_certificate.py | Creating certificates and keys |
| rate_limit.py | Login-specific IP and username checks |
| rate_limit_store.py | Shared counters, expiry and locking |

Existing public imports continue to work. For example, veyon.py imports
capture helpers from veyon_capture.py so callers can still use
`from backend.core.veyon import grab_framebuffer`.

## Small database modules

Every Python file in backend/db has at most 100 lines, including comments
and blank lines. The size-limit test covers both core and db.

Start with database.py to see the public functions. Original modules such as
users.py and schedules.py re-export their functions from smaller modules, so
existing imports still work. The database file stays at data/monitor.db.

| Files | Responsibility |
| --- | --- |
| user_passwords, user_queries | Password rules, hashing, account queries and sign-in checks |
| user_create, user_updates, user_events | Create accounts, update accounts and assign past events |
| alert_rules, alert_policy, notifications | Alert settings, prohibited classes and notifications |
| analytics_filters, analytics_summary, analytics_activity | Shared filters and chart statistics |
| event_counts, event_queries | Count and search detection history |
| detection_events, detection_frames, detection_assignment | Save detections, read screenshots and assign students |
| group_queries, group_updates | Read and update computer groups |
| model_queries, model_updates, model_classes | Read models, update metadata and map classes |
| run_lifecycle, run_queries, run_summary, run_details | Start/finish runs and build report data |
| schedule_queries, schedule_updates | Read and change exam schedules |
| schedule_notifications, schedule_timing | Schedule alert classes, overlaps and active-time checks |
| schema_accounts, schema_schedules, schema_events, schema_models | SQL table definitions |
| schema_seed, schema | Initial data and database setup/migration orchestration |

Names in this table refer to Python files in backend/db. Functions and SQL
were moved by responsibility; the saved database schema was not redesigned.
