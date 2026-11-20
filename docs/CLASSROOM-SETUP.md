# Classroom setup and alarm test

Velarora runs as one server. Every classroom big-screen computer opens that server in its browser. Admins register classrooms and their student PCs; any teacher may choose any classroom. Each exam, its history, screenshots, analytics, reports and schedule belong to the teacher who starts or schedules it. Another teacher cannot take over an active exam. Students have no website access.

## Administrator setup

1. Restart Velarora after updating so its additive database migrations run. Saved records are retained. Old records without a known teacher remain unassigned rather than being given to a random teacher.
2. Open **Classrooms** (the existing Groups page). Create a group for each room and register/assign its PCs. Veyon must already be configured and able to capture those PCs. Use unique PC names such as `Room A - PC 123`.
3. Configure an HTTPS server URL reachable from every classroom and student PC. The TLS certificate must be trusted on those PCs. `http://127.0.0.1` is suitable only for a same-PC test, not a classroom deployment. Keep the server running for automatic schedules.
4. Open **Workstations**, choose one student PC, enter the server URL, and download its agent configuration. A new configuration revokes that PC's previous key; stop and acknowledge its alarms first. Never put these files on GitHub or share a key between PCs.
5. Copy the repository's `workstation` folder and the selected PC's downloaded JSON to that student PC. Install Python 3.12 for all users there if needed, using a base Python location readable by the student Windows account. The agent needs only `psutil`; it does not need PyTorch or the full server dependencies.
6. On that student PC, run the installer in PowerShell **as Administrator**, supplying the actual Python executable and Windows student account:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\workstation\Install-Agent.ps1 -PythonExe "C:\Path\To\Python312\python.exe" -ConfigPath "C:\Path\To\velarora-pc-1.json" -StudentWindowsUser "SCHOOL\examstudent"
```

The installer stores the agent under Program Files and registers an interactive logon task for that Windows account. Repeat account registration for other Windows accounts used on the same PC. Sign out and back in to start it. For a manual test before installing:

```powershell
python -m pip install psutil
python .\workstation\agent.py --config "C:\Path\To\velarora-pc-1.json"
```

The agent runs in the user's desktop session because Windows services cannot directly provide this interactive sound. School Windows policies must control student permissions, muting, process termination and Task Scheduler access; the Python agent by itself is not tamper-proof. Speakers must be connected, enabled and audible. TLS verification stays enabled.

## Teacher workflow

1. Sign in on the big screen and select **This classroom** on Dashboard. That browser remembers the room across teacher sign-ins. For a permanent big-screen startup link, bookmark the room link from Admin → Workstations (for example `https://school-server:8080/?classroom=1`). It restores the room even after closing the browser. No fixed teacher-to-room assignment is required.
2. Set **App Rules**. Blocklist mode alarms only on listed executable names. Allowlist mode alarms on every foreground executable outside the permitted list, so include all required exam tools before enabling it. Names are exact, case-insensitive Windows executable names, for example `notepad.exe`.
3. Start the exam or create a weekly schedule for that classroom. Schedules have their creator's ownership and can run simultaneously in different rooms. The same room/PC cannot be claimed twice. Manual End suppresses that schedule until its current time window ends.
4. A prohibited app creates an alert identifying the PC and application, then the workstation sounds continuously. Closing the app, ending the exam or a short network loss does not clear an active alarm.
5. Use **Stop alarm** on Dashboard or in Notifications. Only the owning teacher can issue it. While the workstation is offline, the UI keeps the stop request visible; the workstation must reconnect and acknowledge silence. The incident and who stopped it remain in the audit records. Clear outstanding alarms before another exam takes over that classroom.
6. After stopping an alarm, the same still-open app does not immediately restart it. Switching away and reopening the blocked app rearms the alarm. Visual model alerts rearm after that prohibited class disappears and appears again.
7. History and reports include foreground executable names from connected agents. Process changes are recorded even without a screenshot. Screenshot-model rules still detect visual interfaces; `chrome.exe` alone cannot distinguish ChatGPT from an allowed website. A trained model and appropriate per-schedule visual rules are needed for that.

## Required real-PC acceptance test

Use two teachers and two registered classrooms. Confirm that each teacher sees only their own exam history/reports, can use the other room after its prior exam ends, and cannot stop the other's alarms. Open a deliberately blocked app on one student PC. Confirm that only that PC sounds, that closing the app and briefly disconnecting its network do not silence it, and that the owning teacher's Stop command silences it after reconnection. Verify the pending-stop message, rearming behavior and a downloaded report. Test schedule start/end with the server online.

Automated tests and browser checks use simulated screen capture/audio. They do not replace this physical speaker, Veyon, certificate and network test. An unavailable agent or muted speaker cannot be made audible by the browser dashboard.
