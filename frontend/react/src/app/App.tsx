import { useCallback, useEffect, useState } from "react";
import {
  Routes,
  Route,
  Navigate,
  NavLink,
  useLocation,
} from "react-router-dom";
import {
  UsersRound,
  School,
  Menu,
  X,
  LogOut,
  Box,
  Settings,
  History,
  UserRound,
  Monitor,
  ArrowUpRight,
} from "lucide-react";
import { api, ApiError, errorText } from "../lib/api";
import type { Session, Notify } from "../lib/types";
import { Button } from "../components/Button/Button";
import { Modal } from "../components/Modal/Modal";
import { Toast, type ToastMessage } from "../components/Toast/Toast";
import { Users } from "../pages/Users/Users";
import { Classrooms } from "../pages/Classrooms/Classrooms";
import styles from "./App.module.css";
export function App() {
  const [session, setSession] = useState<Session | null>(null),
    [error, setError] = useState(""),
    [drawer, setDrawer] = useState(false),
    [logout, setLogout] = useState(false),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState<ToastMessage | null>(null);
  const location = useLocation();
  const notify: Notify = useCallback(
    (text, kind = "success") => setMessage({ id: Date.now(), text, kind }),
    [],
  );
  const dismiss = useCallback(() => setMessage(null), []);
  const load = () => {
    setError("");
    api<Session>("/session")
      .then(setSession)
      .catch((err) => {
        setError(
          err instanceof ApiError && err.status === 401
            ? "Sign in with your administrator account to continue."
            : errorText(err),
        );
      });
  };
  useEffect(load, []);
  useEffect(() => {
    setDrawer(false);
  }, [location.pathname]);
  async function signOut() {
    setBusy(true);
    try {
      await api("/logout", { method: "POST", body: "{}" });
      window.location.assign("/login");
    } catch (err) {
      notify(errorText(err), "error");
      setBusy(false);
    }
  }
  if (!session)
    return (
      <div className={styles.app}>
        <div className={styles.gate}>
          <span className={styles.brand}>Velarora</span>
          <h1>{error ? "Administration" : "Opening your workspace…"}</h1>
          <p role="status">{error || "Preparing your admin dashboard."}</p>
          {error && (
            <>
              <a href="/login">Go to sign in</a>
              <Button onClick={load}>Try again</Button>
            </>
          )}
        </div>
      </div>
    );
  return (
    <div className={styles.app}>
      <aside className={`${styles.sidebar} ${drawer ? styles.open : ""}`}>
        <div className={styles.sidebarTop}>
          <a href="/admin/users" className={styles.brand}>
            Velarora<span>EXAM WORKSPACE</span>
          </a>
          <Button
            variant="ghost"
            aria-label="Close menu"
            onClick={() => setDrawer(false)}
          >
            <X size={20} />
          </Button>
        </div>
        <p className={styles.caption}>ADMINISTRATION</p>
        <nav className={styles.navigation} aria-label="Administration">
          <NavLink
            to="/users"
            className={({ isActive }) => (isActive ? styles.active : "")}
          >
            <UsersRound size={18} />
            Users
          </NavLink>
          <NavLink
            to="/classrooms"
            className={({ isActive }) => (isActive ? styles.active : "")}
          >
            <School size={18} />
            Classrooms
          </NavLink>
          <span className={styles.caption}>MANAGEMENT</span>
          {[
            ["Workstations", "/workstations", Monitor],
            ["Classroom overview", "/classroom-status", Monitor],
            ["Models", "/models", Box],
            ["Model alert rules", "/model-alert-rules", Box],
            ["Audit Log", "/audit", History],
            ["Admin Profile", "/profile", UserRound],
            ["Settings", "/settings", Settings],
          ].map(([label, url, Icon]) => {
            const Component = Icon as typeof Monitor;
            return (
              <a key={String(url)} href={String(url)}>
                <Component size={18} />
                {String(label)}
                <ArrowUpRight size={12} />
              </a>
            );
          })}
        </nav>
        <div className={styles.sidebarBottom}>
          <span className={styles.online}>Local workspace online</span>
          <Button variant="ghost" onClick={() => setLogout(true)}>
            <LogOut size={18} />
            Log out
          </Button>
        </div>
      </aside>
      {drawer && (
        <button
          className={styles.scrim}
          aria-label="Close navigation"
          onClick={() => setDrawer(false)}
        />
      )}
      <div className={styles.workspace}>
        <header className={styles.topbar}>
          <Button
            variant="ghost"
            aria-label="Open menu"
            onClick={() => setDrawer((v) => !v)}
          >
            <Menu size={21} />
          </Button>
          <span>
            Administration <span className={styles.slash}>/</span>{" "}
            {location.pathname.includes("classrooms") ? "Classrooms" : "Users"}
          </span>
          <div className={styles.account}>
            <span className={styles.avatar}>
              {session.user.username.charAt(0).toUpperCase()}
            </span>
            <span>
              {session.user.username}
              <small>Administrator</small>
            </span>
          </div>
        </header>
        <main key={location.pathname} className={styles.main}>
          <Routes>
            <Route
              path="/users"
              element={<Users notify={notify} currentId={session.user.id} />}
            />
            <Route
              path="/classrooms"
              element={<Classrooms notify={notify} />}
            />
            <Route path="*" element={<Navigate to="/users" replace />} />
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
