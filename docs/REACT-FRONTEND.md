# React frontend migration

The first migrated pages are **Admin Users** and **Classrooms**. Login, teacher pages and other admin pages still use the working Python/NiceGUI interface. Existing admin sign-in redirects to React Users once a build exists; `/groups` redirects to React Classrooms. Direct React URLs are `/admin/users` and `/admin/classrooms`.

## Structure

```text
frontend/react/src/
  app/App.tsx + App.module.css
  components/
    Button/Button.tsx + Button.module.css
    Input/Input.tsx + Input.module.css
    Modal/Modal.tsx + Modal.module.css
    StatCard/StatCard.tsx + StatCard.module.css
    DataTable/DataTable.tsx + DataTable.module.css
    PageHeading/PageHeading.tsx + PageHeading.module.css
    Toast/Toast.tsx + Toast.module.css
  pages/
    Users/Users.tsx + Users.module.css
    Classrooms/Classrooms.tsx + Classrooms.module.css
  lib/api.ts + types.ts
```

Components own their styles through CSS Modules. There is no shared global component stylesheet. The HTML document only sets the base margin/background. Local font declarations and application layout belong to App.module.css. Reduced-motion preferences are respected.

## Build and run

Node.js 20.19+ or 22.12+ is required by the build tools. From the project directory:

```powershell
cd frontend/react
npm ci
npm run build
cd ../..
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Monitor.ps1
```

Restart the Python server after the first React build so `/admin/assets` is registered. No second production server is required. Builds and node_modules are ignored in Git; source and package-lock.json are committed. Without a built React frontend, existing NiceGUI Users/Classrooms remain available.

`npm run dev` starts Vite for frontend development and proxies API requests to the local Python server. Sign-in uses the existing same-origin browser session; use the built frontend for full integration testing.

The admin JSON API is under `/api/admin`. Every request rechecks the account's live admin role. Mutations require a session-bound CSRF token. Password hashes are never returned. Existing classroom, monitoring and deletion safeguards are reused. The next migration sections are login and the remaining admin/teacher pages.
