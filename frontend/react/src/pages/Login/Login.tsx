import { useState, type FormEvent } from "react";
import { useLocation } from "react-router-dom";
import { Mail } from "lucide-react";
import { api, json, errorText } from "../../lib/api";
import type { Session } from "../../lib/types";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import { Check } from "../../components/Check/Check";
import { Modal } from "../../components/Modal/Modal";
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
    if (busy) return;
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
      title="Sign in"
      description="Access your Velarora exam workspace."
      onSubmit={submit}
      aside={
        <>
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
          <p className={styles.divider}>or</p>
          <a
            className={styles.google}
            href={"/auth/google?remember=" + remember}
          >
            <span className={styles.googleMark} aria-hidden="true">
              <svg
                viewBox="0 0 48 48"
                width="18"
                height="18"
                aria-hidden="true"
              >
                <path
                  fill="#EA4335"
                  d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z"
                />
                <path
                  fill="#4285F4"
                  d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6C44.4 38.02 46.98 31.88 46.98 24.55Z"
                />
                <path
                  fill="#FBBC05"
                  d="M10.53 28.59A14.5 14.5 0 0 1 9.75 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.9 23.9 0 0 0 0 24c0 3.87.93 7.53 2.56 10.78l7.97-6.19Z"
                />
                <path
                  fill="#34A853"
                  d="M24 48c6.48 0 11.93-2.13 15.91-5.8l-7.73-6c-2.15 1.45-4.92 2.3-8.18 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z"
                />
              </svg>
            </span>
            Continue with Google
          </a>
        </>
      )}
      <p className={styles.accountHelp}>
        Accounts are provided by your school administrator.
      </p>
    </AuthLayout>
  );
}
