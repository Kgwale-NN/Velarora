# React frontend

All active browser pages use React and TypeScript. The Python backend retains authentication, monitoring, AI training, schedules, reports and workstation alarms. NiceGUI supplies the existing ASGI server and session storage; its old page modules are no longer registered.

## Pages


- Sign-in: email/password, remember me, Google sign-in and password-reset guidance.
- Account creation: administrators add teachers from Users → Add user. Public sign-up is disabled.
- Administrator: Users, Classrooms, Workstations, Classroom overview, Models and training, Model alert rules, Audit log, Profile and Settings.
- Teacher: Dashboard, History, Analytics, Reports, Schedules, App rules, Notifications and Profile.
- Students remain monitoring records and have no website sign-in access.

The app opens at login for signed-out visitors. Old welcome/sign-up links return to login.

Historical bookmarks such as `/login`, `/users`, `/groups`, `/history` and `/models` redirect to the React app. The existing SPA base is `/admin/` for both staff roles; this URL prefix grants no administrator permissions. The sidebar and backend independently enforce roles.

## Folder structure

```text
frontend/react/src/
  app/                  # Role-aware routing and workspace shell
  components/           # Reusable Button, Input, Select, Modal, tables,
                        # panels, notifications, snapshots and charts
  pages/
    Login/
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

- `/api/session`, `/api/login`, `/api/logout`, `/api/profile`: staff account operations.
- `/api/admin/*`: live administrator role checks on every request.
- `/api/teacher/*`: teacher-owned history, reports, schedules, rules, notifications, alarms and exam controls.
- `/api/classrooms/*`: shared classroom selection; screen data is visible to the owning teacher or an administrator.
- `/api/workstation/heartbeat`: existing authenticated agent channel.

Browser mutations require the session CSRF token. Queries enter teacher scope inside the executor thread. Password hashes and saved logon passwords never leave the backend. Provisioned workstation secrets are returned only when generating the selected PC configuration. ZIP uploads validate paths and extraction limits.

Training runs in the existing background worker and survives navigation. Dataset upload/server-folder analysis, automatic missing splits, import, activation, metadata editing, class synchronisation, deletion safeguards, fine-tuning, progress and cancellation are available in React. Fine-tuning matches class names and requires confirmation before appending new classes. Hardware status is informational: the frontend does not uninstall a working CPU PyTorch installation.

The old `frontend/pages` files are retained as inactive migration references and for existing regression tests. They are not imported by application startup or linked from the React navigation.

## Teacher dashboard design

Every teacher page uses the same light black-and-white theme. The dashboard uses this theme with the login's system font, a compact sidebar, classroom controls, and three summary cards. Theme values live in the scoped App CSS Module; shared buttons, panels, selects, statistics, dialogs and notifications consume those values and keep their previous defaults elsewhere.

Live computer cards are in `components/ComputerScreen`, with their own TSX and CSS Module. They show online, offline and waiting states and open a larger live preview. Classroom PC totals come from classroom membership; online totals come from recent captures. Alarm totals include stop commands awaiting workstation acknowledgement. Alarms from the teacher's other exams remain visible and show their classroom.

Start/stop controls retain the existing APIs and ownership checks. Another teacher's active classroom cannot be controlled from this page. Loading and empty states explain missing classrooms, missing PCs and pending captures. On smaller screens, the menu becomes a drawer. Active alarm controls are available through notifications.

The teacher shell applies its palette across History, Analytics, Reports, Schedules, App Rules, Notifications and Profile. Shared tables, charts, input hints, forms and dialogs use scoped theme values for readable text and borders. Administrator pages now share the same light palette, font, spacing, tables and controls.

The sidebar account control is a reusable `AccountMenu` component. Its bottom name-and-avatar block opens a glass popover with Profile and Log out. The duplicate top-right profile and account role caption are removed. The popover uses a portal so it is not clipped by the scrolling sidebar, stays inside the viewport, supports keyboard navigation and Escape, and closes on outside clicks. Logging out still requires the existing confirmation dialog. Both roles use the same light glass account menu.

The reusable Sidebar component supports an expanded desktop menu and a 64px icon rail. The header toggle remembers the preference in localStorage. Compact links keep accessible names and hover titles; the bottom account menu remains available in either view. Phones use the full drawer, with Escape, outside-click dismissal, keyboard focus handling and hidden-menu inertness. Width transitions respect reduced-motion preferences. Sidebar styles live in its own CSS Module.


## Shared navigation and form controls

HeroUI's Navbar, ScrollShadow, Select and Spinner packages are wrapped by reusable components with local CSS Modules. The header remains above the scrolling workspace, while 40px overflow fades indicate more page or sidebar content. Both roles share the light black-and-white palette. Select popovers inherit their theme explicitly and mount inside an existing native dialog when used in a form popup. Select callbacks receive the selected string value.

Sign-in and logout show an 18px loading spinner and progress text, with duplicate submissions disabled. Submit buttons use the primary style; other buttons default to type=button. Bordered toasts appear at bottom-right, pause dismissal while hovered or focused, and expose a dismiss button. Manual page refresh buttons have been removed; browser refresh and existing automatic polling remain. The model library reloads automatically when a training result becomes available. Secondary pages load on demand with a skeleton fallback.


The dashboard focuses on live screens: the monitoring-activity log and permanent exam-alarm sidebar are removed. A shared ExamAlarmsProvider polls the owning teacher's alarms once across pages. New alarms open a persistent bottom-right notification with PC, app, classroom and Stop alarm. Dismissing that notification does not stop the workstation siren. The notification bell opens the active-alarm list; the full Notifications page includes the same controls. Stop commands retain the existing teacher-scoped backend endpoint and pending-acknowledgement state.

The sidebar no longer shows the Profile navigation link or the Local workspace online label. Profile remains available in the bottom account menu. Sign-in and sign-out display a centred glass progress dialog with a 28px spinner for the actual request duration; no artificial delay is added. Administrator-specific tables, filters and page headings use the shared light theme and compact spacing.


## Consistent workspace page structure

All 17 teacher and administrator workspace routes use the shared PageHeading for title, supporting description and right-aligned actions. Content follows a 20px section rhythm, with 12px cards, compact filters and uniform table headers/cell spacing. Workspace button and input sizes/radii use scoped theme values; the login now matches the compact field and button styling. FormActions aligns save/submit controls below a separator in Profile, App Rules and Settings. EmptyState is shared by both table components. Models gives Train new model the primary action style. Glass remains on navigation, notifications and dialogs; content surfaces favour readability. Existing page APIs, authorization, monitoring and alarm behaviour are unchanged.


The login uses the same compact black-and-white interface direction: a short heading and description, labelled 40px fields, 10px field corners, 8px button corners, a flat black primary action and an outlined Google action. The lab image remains as a subdued decorative background. Authentication, Remember me, password visibility, administrator reset guidance and sign-in progress remain unchanged. Desktop and phone widths are verified with mock authentication requests.


PageSkeleton provides reusable, route-specific loading layouts for all workspace pages. Dashboard placeholders include controls, statistics and screen cards; list/table pages show matching structures; Profile shows two forms; Settings shows its sections; App Rules includes its large text area. Lazy route loading and initial API loading use the same layout. Existing content remains during normal polling, motion preferences are respected, and no artificial loading delay is added. ResourceState can use compact table, form or list variants for independent requests.


The login uses a split desktop layout: the form is centred in the left half and the clear computer-lab2 image fills the right half. On screens up to 800px, the image stacks below the form. Existing sign-in controls and authentication behaviour are retained.
