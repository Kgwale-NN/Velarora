import { useState, type FormEvent } from "react";
import { useLocation } from "react-router-dom";
import { Mail } from "lucide-react";
import { api, json, errorText } from "../../lib/api";
import type { Session } from "../../lib/types";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import { Check } from "../../components/Check/Check";
import { Modal } from "../../components/Modal/Modal";
import { AuthProgress } from "../../components/AuthProgress/AuthProgress";
import { AuthLayout } from "../../components/AuthLayout/AuthLayout";
import { PasswordField } from "../../components/PasswordField/PasswordField";
import styles from "./Login.module.css";
export function Login({
  session,
  onLogin,
}: {
  session: Session;
  onLogin: (s: Session) => void;
}) {
  const location = useLocation();
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [remember, setRemember] = useState(false),
    [busy, setBusy] = useState(false),
    [forgot, setForgot] = useState(false),
    [error, setError] = useState(
      new URLSearchParams(location.search).has("google")
        ? "Google sign-in did not finish. Check your computer clock or sign in with your password."
        : "",
    );
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onLogin(
        await api<Session>(
          "/login",
          json("POST", { email, password, remember }),
        ),
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <AuthLayout
      title="Log in to your exam workspace."
      onSubmit={submit}
      aside={
        <>
          {busy && <AuthProgress label="Signing in..." />}
          {forgot && (
            <Modal title="Reset your password" onClose={() => setForgot(false)}>
              <p>
                Ask your school administrator to reset your account password.
                Give them the email address you use to sign in.
              </p>
              <Button onClick={() => setForgot(false)}>Got it</Button>
            </Modal>
          )}
        </>
      }
    >
      <Input
        label="Email address"
        placeholder="Email address"
        type="email"
        autoComplete="username"
        icon={<Mail size={18} />}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <PasswordField
        label="Password"
        placeholder="Password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <div className={styles.row}>
        <Check
          label="Remember me"
          checked={remember}
          onChange={(e) => setRemember(e.target.checked)}
        />
        <button type="button" onClick={() => setForgot(true)}>
          Forgot password?
        </button>
      </div>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      <Button variant="primary" type="submit" busy={busy}>
        {busy ? "Signing in..." : "Sign in"}
      </Button>
      {session.google && (
        <>
          <p className={styles.divider}>or continue with</p>
          <a
            className={styles.google}
            href={"/auth/google?remember=" + remember}
          >
            <span className={styles.googleMark} aria-hidden="true">
              G
            </span>
            Google
          </a>
        </>
      )}
    </AuthLayout>
  );
}
