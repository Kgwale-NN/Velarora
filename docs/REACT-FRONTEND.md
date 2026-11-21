# React frontend

All active browser pages use React and TypeScript. The Python backend retains authentication, monitoring, AI training, schedules, reports and workstation alarms. NiceGUI supplies the existing ASGI server and session storage; its old page modules are no longer registered.

## Pages

- Sign-in: email/password, remember me, Google sign-in and password-reset guidance.
- Teacher sign-up: public registration with full name, email, strong password and confirmation. New accounts can sign in as teachers; administrator roles cannot be selected. Email verification is not configured yet.
- Administrator: Users, Classrooms, Workstations, Classroom overview, Models and training, Model alert rules, Audit log, Profile and Settings.
- Teacher: Dashboard, History, Analytics, Reports, Schedules, App rules, Notifications and Profile.
- Students remain monitoring records and have no website sign-in access.

Historical bookmarks such as `/login`, `/users`, `/groups`, `/history` and `/models` redirect to the React app. The existing SPA base is `/admin/` for both staff roles; this URL prefix grants no administrator permissions. The sidebar and backend independently enforce roles.

## Folder structure

```text
frontend/react/src/
  app/                  # Role-aware routing and workspace shell
  components/           # Reusable Button, Input, Select, Modal, tables,
                        # panels, notifications, snapshots and charts
  pages/
    Login/
    Signup/
    Users/
    Classrooms/
    Dashboard/
    History/
    Analytics/
    Reports/
    Schedules/ScheduleEditor/
    Models/ImportModel/
    Models/TrainingForm/
    ...
  lib/                  # API client, types and request lifecycle hook
```

Each page and component owns its `.tsx` and `.module.css` files. Component appearance does not depend on a global CSS stylesheet. The document only sets a base margin/background. Shared controls keep the black glass theme, local font, gentle movement, keyboard support and reduced-motion support. Modal content does not close the dialog; clicking the backdrop (including right-clicking) does.

## Running locally

Install Node.js 22.12+ or Node.js 24 LTS. From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Monitor.ps1
```

The launcher installs frontend dependencies when needed and builds React when source files change. Open `http://127.0.0.1:8080`. After updating backend code, stop the old server with Ctrl+C and restart it.

Manual frontend build:

```powershell
cd frontend/react
npm ci
npm run build
cd ../..
```

For frontend development, run the Python backend and `npm run dev` in `frontend/react`. Vite proxies `/api`, `/auth` and `/design-assets` to port 8080. Use the production build on port 8080 when testing the Google OAuth callback registered for that origin.

Build output and `node_modules` are ignored by Git. Source files and the lockfile are committed. GitHub CI checks the React build; the Windows executable build includes compiled React assets, fonts and report translations without bundling `node_modules`.

## Backend contracts

- `/api/session`, `/api/login`, `/api/signup`, `/api/logout`, `/api/profile`: staff account operations.
- `/api/admin/*`: live administrator role checks on every request.
- `/api/teacher/*`: teacher-owned history, reports, schedules, rules, notifications, alarms and exam controls.
- `/api/classrooms/*`: shared classroom selection; screen data is visible to the owning teacher or an administrator.
- `/api/workstation/heartbeat`: existing authenticated agent channel.

Browser mutations require the session CSRF token. Queries enter teacher scope inside the executor thread. Password hashes and saved logon passwords never leave the backend. Provisioned workstation secrets are returned only when generating the selected PC configuration. ZIP uploads validate paths and extraction limits.

Training runs in the existing background worker and survives navigation. Dataset upload/server-folder analysis, automatic missing splits, import, activation, metadata editing, class synchronisation, deletion safeguards, fine-tuning, progress and cancellation are available in React. Fine-tuning matches class names and requires confirmation before appending new classes. Hardware status is informational: the frontend does not uninstall a working CPU PyTorch installation.

The old `frontend/pages` files are retained as inactive migration references and for existing regression tests. They are not imported by application startup or linked from the React navigation.
