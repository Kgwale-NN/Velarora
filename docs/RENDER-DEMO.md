# Free Render demonstration

This is an inference-only, disposable demonstration. It does not replace a school's Windows workstation installation. The Docker build excludes your private .env, database, screenshot records, keys and trained weights. It starts a separate database and admin account.

## Current status

The deployment foundation serves the React app and staff APIs without loading PyTorch at startup. Windows/Veyon exam start is explicitly blocked in this mode. Browser screen sharing and browser inference still need implementation and an end-to-end test before a venue demonstration. Deploying the current foundation alone does not enable monitoring the venue PC.

## Free limitations

Render's free web service has 512 MB RAM, sleeps after 15 minutes without inbound traffic, and loses local changes on restart/redeploy/sleep. Accounts, sessions, uploads, models and exam records on this disposable instance can be lost. Download reports before stopping a demonstration. Keep your working desktop installation as your original copy. This mode disables scheduled Windows exams and does not include model training or CUDA installation. AI inference memory and speed must be tested, not assumed.

## Deployment steps

1. In Render choose **New > Blueprint**, connect GitHub and select `Kgwale-NN/Velarora` on `main`.
2. Render reads `render.yaml`. Check the service is **Free** and that there are no paid disks or databases before applying it.
3. Set `INITIAL_ADMIN_EMAIL` to your admin email. Set `INITIAL_ADMIN_PASSWORD` to a new strong password in Render only. Do not send it in chat. This is a separate cloud account; your desktop credentials and teacher accounts are not copied.
4. Apply the Blueprint. Docker builds the React frontend and installs the lighter Python dependencies. No separate build or start command is needed.
5. Once deployed, open the service URL followed by `/admin/login`. Check `/healthz` returns status ok, then sign in and create a teacher account.
6. Do not rely on screen monitoring until browser sharing/inference has been added and verified. An ONNX model will need a trusted upload or an explicitly approved demo asset; the private trained model is not in GitHub.

If using **New > Web Service** instead, select the repository, Docker runtime, Free instance, and health path `/healthz`. Add a random `STORAGE_SECRET` and the three `INITIAL_ADMIN_*` variables manually. Docker supplies the cloud-mode settings. Keep one instance because the app uses SQLite and in-memory exam ownership.

Google sign-in is optional: register the exact public `/auth/google/callback` URL in Google Cloud, then set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `GOOGLE_REDIRECT_URI` in Render. Email/password is the initial verification path.

References: https://render.com/docs/free , https://render.com/docs/blueprint-spec , https://render.com/docs/docker
