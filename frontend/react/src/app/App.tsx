import { useCallback, useEffect, useState } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import {
  UsersRound,
  School,
  Box,
  Settings as SettingsIcon,
  History as HistoryIcon,
  UserRound,
  Monitor,
  Bell,
  Calendar,
  ChartColumn,
  FileText,
  Shield,
} from "lucide-react";
import { api, json, errorText } from "../lib/api";
import type { Session, Notify } from "../lib/types";
import { Button } from "../components/Button/Button";
import { Modal } from "../components/Modal/Modal";
import { Toast, type ToastMessage } from "../components/Toast/Toast";
import { ResourceState } from "../components/ResourceState/ResourceState";
import { Users } from "../pages/Users/Users";
import { Classrooms } from "../pages/Classrooms/Classrooms";
import { Login } from "../pages/Login/Login";
import { Dashboard } from "../pages/Dashboard/Dashboard";
import { History } from "../pages/History/History";
import { Analytics } from "../pages/Analytics/Analytics";
import { Reports } from "../pages/Reports/Reports";
import { Schedules } from "../pages/Schedules/Schedules";
import { AppRules } from "../pages/AppRules/AppRules";
import { Profile } from "../pages/Profile/Profile";
import { Notifications } from "../pages/Notifications/Notifications";
import { Workstations } from "../pages/Workstations/Workstations";
import { Models } from "../pages/Models/Models";
import { Audit } from "../pages/Audit/Audit";
import { Settings } from "../pages/Settings/Settings";
import { ModelRules } from "../pages/ModelRules/ModelRules";
import { NotificationBell } from "../components/NotificationBell/NotificationBell";
import { SidebarToggle } from "../components/SidebarToggle/SidebarToggle";
import { Sidebar } from "../components/Sidebar/Sidebar";
import { useSmallScreen } from "../lib/useSmallScreen";
import styles from "./App.module.css";
const adminLinks = [
  ["Users", "/users", UsersRound],
  ["Classrooms", "/classrooms", School],
  ["Workstations", "/workstations", Monitor],
  ["Classroom overview", "/classroom-overview", Monitor],
  ["Models", "/models", Box],
  ["Model alert rules", "/model-alert-rules", Shield],
  ["Audit log", "/audit", HistoryIcon],
  ["Profile", "/profile", UserRound],
  ["Settings", "/settings", SettingsIcon],
] as const;
const teacherLinks = [
  ["Dashboard", "/dashboard", Monitor],
  ["History", "/history", HistoryIcon],
  ["Analytics", "/analytics", ChartColumn],
  ["Reports", "/reports", FileText],
  ["Schedules", "/schedules", Calendar],
  ["App rules", "/app-rules", Shield],
  ["Notifications", "/notifications", Bell],
  ["Profile", "/profile", UserRound],
] as const;
export function App() {
  const [session, setSession] = useState<Session | null>(null),
    [error, setError] = useState(""),
    [drawer, setDrawer] = useState(false),
    [collapsed, setCollapsed] = useState(
      () => localStorage.getItem("velarora.sidebar.compact") === "true",
    ),
    [logout, setLogout] = useState(false),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState<ToastMessage | null>(null);
  const mobile = useSmallScreen();
  const location = useLocation();
  useEffect(() => {
    if (!mobile) setDrawer(false);
  }, [mobile]);
  const notify: Notify = useCallback(
    (text, kind = "success") => setMessage({ id: Date.now(), text, kind }),
    [],
  );
  const dismiss = useCallback(() => setMessage(null), []);
  const load = useCallback(() => {
    setError("");
    api<Session>("/session")
      .then(setSession)
      .catch((e) => setError(errorText(e)));
  }, []);
  useEffect(load, [load]);
  useEffect(() => {
    setDrawer(false);
    const room = new URLSearchParams(location.search).get("classroom");
    if (room && /^\d+$/.test(room))
      localStorage.setItem("velarora.classroom", room);
  }, [location.pathname, location.search]);
  if (!session)
    return (
      <div className={styles.app}>
        <div className={styles.gate}>
          <span className={styles.brand}>Velarora</span>
          <h1>Opening your workspace</h1>
          <ResourceState loading={!error} error={error} retry={load} />
        </div>
      </div>
    );
  if (!session.user)
    return (
      <>
        {location.pathname !== "/login" ? (
          <Navigate to={"/login" + location.search} replace />
        ) : (
          <Login session={session} onLogin={setSession} />
        )}
        <Toast message={message} onDismiss={dismiss} />
      </>
    );
  const user = session.user,
    admin = user.role === "admin",
    links = admin ? adminLinks : teacherLinks,
    home = admin ? "/users" : "/dashboard";
  const title =
    links.find((l) => l[1] === location.pathname)?.[0] || "Workspace";
  async function signOut() {
    setBusy(true);
    try {
      await api("/logout", json("POST"));
      setLogout(false);
      setSession(null);
      load();
    } catch (e) {
      notify(errorText(e), "error");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div
      className={`${styles.app} ${!admin ? styles.teacher : ""} ${collapsed && !mobile ? styles.compact : ""}`}
    >
      <Sidebar
        name={user.username}
        role={user.role}
        home={home}
        links={links}
        collapsed={collapsed && !mobile}
        mobile={mobile}
        open={drawer}
        onClose={() => setDrawer(false)}
        onLogout={() => {
          setDrawer(false);
          setLogout(true);
        }}
      />
      <div className={styles.workspace}>
        <header className={styles.topbar}>
          <SidebarToggle
            open={mobile ? drawer : !collapsed}
            onClick={() => {
              if (mobile) setDrawer((v) => !v);
              else {
                const next = !collapsed;
                setCollapsed(next);
                localStorage.setItem("velarora.sidebar.compact", String(next));
              }
            }}
          />
          <span className={styles.breadcrumb}>
            {admin ? "Administration" : "Teacher"}{" "}
            <span className={styles.slash}>/</span> {title}
          </span>
          {!admin && <NotificationBell notify={notify} />}
        </header>
        <main key={location.pathname} className={styles.main}>
          <Routes>
            {admin ? (
              <>
                <Route
                  path="/users"
                  element={<Users notify={notify} currentId={user.id} />}
                />
                <Route
                  path="/classrooms"
                  element={<Classrooms notify={notify} />}
                />
                <Route
                  path="/workstations"
                  element={<Workstations notify={notify} />}
                />
                <Route
                  path="/classroom-overview"
                  element={<Dashboard notify={notify} overview />}
                />
                <Route path="/models" element={<Models notify={notify} />} />
                <Route
                  path="/model-alert-rules"
                  element={<ModelRules notify={notify} />}
                />
                <Route path="/audit" element={<Audit />} />
                <Route
                  path="/settings"
                  element={<Settings notify={notify} />}
                />
              </>
            ) : (
              <>
                <Route
                  path="/dashboard"
                  element={<Dashboard notify={notify} />}
                />
                <Route path="/history" element={<History />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/reports" element={<Reports notify={notify} />} />
                <Route
                  path="/schedules"
                  element={<Schedules notify={notify} />}
                />
                <Route
                  path="/app-rules"
                  element={<AppRules notify={notify} />}
                />
                <Route
                  path="/notifications"
                  element={<Notifications notify={notify} />}
                />
              </>
            )}
            <Route
              path="/profile"
              element={<Profile notify={notify} onUpdated={load} />}
            />
            <Route path="*" element={<Navigate to={home} replace />} />
          </Routes>
          <footer className={styles.footer}>
            Velarora <span>Classrooms connected. Exams protected.</span>
          </footer>
        </main>
      </div>
      <Toast message={message} onDismiss={dismiss} />
      {logout && (
        <Modal
          title="Log out of Velarora?"
          onClose={() => setLogout(false)}
          busy={busy}
        >
          <p>You will return to the sign-in page.</p>
          <footer>
            <Button onClick={() => setLogout(false)} disabled={busy}>
              Stay here
            </Button>
            <Button variant="primary" onClick={signOut} busy={busy}>
              Log out
            </Button>
          </footer>
        </Modal>
      )}
    </div>
  );
}
