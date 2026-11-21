# Free Render demonstration

This is an inference-only, disposable demonstration. It does not replace a school's Windows workstation installation. The Docker build excludes your private .env, database, screenshot records, keys and trained weights. It starts a separate database and admin account.

## Current status

The React teacher dashboard includes **Share screen**. It requests the browser's screen-sharing permission, sends one JPEG at a time to CPU ONNX inference, and saves detections in the owning teacher's history, analytics and reports. Enabled model alert rules latch a browser alarm; that teacher can silence it. A stopped alarm rearms only after the blocked application disappears from a subsequent captured picture. Screens are checked approximately every two seconds plus inference/network time. Windows/Veyon exam start remains explicitly blocked in this mode.

Use desktop Chrome or Edge and select **Entire screen** to detect applications outside the browser. Browsers cannot silently read process names, force unmutable sound or keep capturing after a person closes the sharing page. Keep the teacher dashboard tab open while switching to Notepad. Ending sharing, browser permission revocation or leaving the dashboard releases the screen and sound. The Windows agent remains the option for a protected classroom alarm.

## Free limitations

Render's free web service has 512 MB RAM, sleeps after 15 minutes without inbound traffic, and loses local changes on restart/redeploy/sleep. Accounts, sessions, uploads, models and exam records on this disposable instance can be lost. Download reports before stopping a demonstration. Keep your working desktop installation as your original copy. This mode disables scheduled Windows exams and does not include model training or CUDA installation. AI inference memory and speed must be tested, not assumed.

## Deployment steps

1. In Render choose **New > Blueprint**, connect GitHub and select `Kgwale-NN/Velarora` on `main`.
2. Render reads `render.yaml`. Check the service is **Free** and that there are no paid disks or databases before applying it.
3. Set `INITIAL_ADMIN_EMAIL` to your admin email. Set `INITIAL_ADMIN_PASSWORD` to a new strong password in Render only. Do not send it in chat. This is a separate cloud account; your desktop credentials and teacher accounts are not copied.
4. Apply the Blueprint. Docker builds the React frontend and installs the lighter Python dependencies. No separate build or start command is needed.
5. Once deployed, open the service URL followed by `/admin/login`. Check `/healthz` returns status ok, then sign in and create a teacher account.
6. As admin, open **Models > Import model**, upload trusted ONNX weights exported at 640 pixels or smaller, and activate the model. PT uploads and model training are disabled in this cloud mode. Model uploads are limited to 32 MB to fit the demo's memory budget. The private trained model is not in GitHub.
7. Open **Model alert rules** and enable the class you want to demonstrate (for example, Notepad). Detections still appear in history when an alert rule is disabled, but no alarm should sound for that class.
8. Sign in as the teacher. Click **Share screen**, approve **Entire screen**, then open Notepad and wait for a result. Verify the detection and browser sound at the venue. Return to the dashboard and click **Stop browser alarm**. Close Notepad, allow a clear picture, and reopen it to check rearming.
9. Click **End sharing** before navigating to History, Analytics or Reports. Verify the saved session and download the report. Actual audible output and genuine sharing permissions need a test on the venue PC; automated browser tests cannot establish that its speakers work.

When updating an existing deployment, use **Manual Deploy > Deploy latest commit** in the Render service. The Blueprint disables automatic code deploys so a GitHub push does not unexpectedly interrupt a demonstration. A free redeploy may erase existing cloud accounts and weights, so repeat the model upload and teacher account setup if necessary.

Only one teacher's shared screen is processed at a time on this free demo. Another teacher cannot submit pictures, stop the alarm or end that teacher's session. Sessions with no successful capture for two minutes can be replaced; restarting sharing also interrupts the owner's previous session. This limit is deliberately narrower than the Windows classroom deployment.

Local verification exercised the real ONNX model through the cloud-mode backend and Chrome, using a simulated shared screen containing a saved Notepad test picture. It covered denied permission, detection, alarm state, teacher silence, screen-ended handling, full-page navigation cleanup and saved history. The local server and AI used approximately 146 MB RSS in that check; this is not a measured Render memory guarantee or a physical sound test. Genuine screen sharing and audible alarms still require verification after the Render update.

If using **New > Web Service** instead, select the repository, Docker runtime, Free instance, and health path `/healthz`. Add a random `STORAGE_SECRET` and the three `INITIAL_ADMIN_*` variables manually. Docker supplies the cloud-mode settings. Keep one instance because the app uses SQLite and in-memory exam ownership.

Google sign-in is optional: register the exact public `/auth/google/callback` URL in Google Cloud, then set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `GOOGLE_REDIRECT_URI` in Render. Email/password is the initial verification path.

References: https://render.com/docs/free , https://render.com/docs/blueprint-spec , https://render.com/docs/docker
