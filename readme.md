# Velarora

Computer monitoring for supervised exams. Built with Python and NiceGUI, using Veyon for screen capture and YOLO for image detection.

## Start the app

On a fresh clone, follow the [Windows setup guide](docs/LOCAL-SETUP.md) first. Then open this project folder in VS Code and press **Ctrl+Shift+B**, or run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Monitor.ps1
```

Open http://127.0.0.1:8080. Keep the terminal open. Stop with Ctrl+C.
The older root Start-Monitor.ps1 command still works.

## Find your code

| Folder | What belongs here |
| --- | --- |
| backend | Database, AI processing, monitoring, scheduling and authentication |
| frontend | Pages, navigation, translations and interface assets |
| tests/unit and tests/database | Application checks and database tests |
| scripts | Startup and Windows build tools |
| docs | Setup instructions and project explanations |
| data (created locally) | Saved records, datasets and logs; excluded from Git |

Both frontend and backend run together in one Python process.

- [Setup guide](docs/LOCAL-SETUP.md)
- [Folder guide and bug-finding tips](docs/PROJECT-STRUCTURE.md)
- [Original project documentation](docs/UPSTREAM.md)

## Credits and licence

Based on [Veyon AI Monitor by Marius Vainauskis](https://github.com/vainmari/Veyon-detection).
Original credits are retained. See [LICENSE](LICENSE) for the AGPL-3.0 licence.
