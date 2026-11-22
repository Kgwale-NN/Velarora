# Velarora portable campus PC

This is the Windows 64-bit workstation app. Copy the **whole folder**, including
`_internal`, onto the campus PC or a USB drive. Python and Veyon do not need to be
installed on that PC. Your home desktop still runs Velarora, the AI and the HTTPS
tunnel, so it must stay on and connected to the internet.

## Before travelling

1. Start Velarora and its demo link on the home desktop.
2. Sign in as admin. Create a separate classroom, such as **Campus Demonstration**.
3. Open **Workstation setup**, add **Campus Demo PC** to that classroom, and
   download its configuration using your current HTTPS demo server address.
4. Copy that configuration into this portable folder and rename it **agent.json**.
   Never share it publicly: it is this PC's private connection key.
5. Copy the folder to USB. If the demo address changes, download a new
   configuration before using the app. Do not reuse one PC's configuration on
   several PCs at once.

## At campus

1. Open **Velarora-Agent.exe** on the campus PC.
2. Tick the permission box and press **Connect**. Both connected monitors are
   included. Screenshots begin only when a teacher starts this PC's exam.
3. In the browser, open the home desktop's HTTPS demo link and sign in as teacher.
4. Select **Campus Demonstration**, then start monitoring. Do not select your
   home desktop's Local Test classroom.
5. To test a known Windows app reliably, add **notepad.exe** under the teacher's
   prohibited **App rules** before the exam. Bring Notepad to the foreground.
   The native app rule is separate from the AI's screenshot predictions.
6. Check that the dashboard shows the campus PC. Stop any alarm from the owning
   teacher's dashboard, then end monitoring and disconnect the app.

The internet and speakers must work. Campus IT may restrict running downloaded
programs or outbound traffic: follow its rules. The app has a visible window and
requests permission. This is a demonstration client, not a locked-down kiosk;
Windows Task Manager can terminate it. If a connection fails during an alarm,
the alarm stays on until the teacher's stop command reaches the app. Reconnect
to receive that command. Logs contain error types, not connection keys.

Screens are resized to fit 1920×1080 for upload, so small windows across multiple
monitors may be harder for the visual model to recognise. An app rule checks the
foreground executable; it does not list every background process. AI confidence
is a prediction and still needs validation on separate test screenshots.

## Build from source (on Windows)

From the Velarora project folder:

```powershell
.\.venv\Scripts\python.exe -m venv data\agent-build\venv
.\data\agent-build\venv\Scripts\python.exe -m pip install pyinstaller -r workstation\requirements.txt
.\scripts\Build-Workstation.ps1
```

Output: `data\portable\Velarora-Agent`. Generated binaries and configurations
stay out of Git. A new package needs the administrator's `agent.json` beside the
executable. Never bundle an administrator password or the desktop's `.env`.
