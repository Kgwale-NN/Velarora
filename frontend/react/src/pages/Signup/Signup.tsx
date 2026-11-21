import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Mail, UserRound } from "lucide-react";
import { AuthLayout } from "../../components/AuthLayout/AuthLayout";
import { Input } from "../../components/Input/Input";
import { PasswordField } from "../../components/PasswordField/PasswordField";
import { Button } from "../../components/Button/Button";
import { api, json, errorText } from "../../lib/api";
import styles from "./Signup.module.css";
export function Signup() {
  const navigate = useNavigate();
  const [name, setName] = useState(""),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [confirm, setConfirm] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Your passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api(
        "/signup",
        json("POST", {
          username: name,
          email,
          password,
          confirm_password: confirm,
        }),
      );
      setPassword("");
      setConfirm("");
      navigate("/login", {
        replace: true,
        state: { registeredEmail: email.trim().toLowerCase() },
      });
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <AuthLayout title="Create your teacher account." onSubmit={submit}>
      <Link to="/login" className={styles.back} aria-label="Back to sign in">
        <ArrowLeft size={20} />
      </Link>
      <Input
        label="Full name"
        placeholder="Full name"
        autoComplete="name"
        icon={<UserRound size={18} />}
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={100}
        required
        disabled={busy}
      />
      <Input
        label="Email address"
        placeholder="Email address"
        type="email"
        autoComplete="email"
        icon={<Mail size={18} />}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        maxLength={254}
        required
        disabled={busy}
      />
      <PasswordField
        label="Password"
        placeholder="Create a password"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        minLength={12}
        maxLength={72}
        required
        disabled={busy}
        aria-describedby="password-help"
      />
      <p id="password-help" className={styles.help}>
        Use at least 12 characters. Start with a capital letter and include a
        number and a symbol.
      </p>
      <PasswordField
        label="Confirm password"
        placeholder="Repeat your password"
        autoComplete="new-password"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        minLength={12}
        maxLength={72}
        required
        disabled={busy}
      />
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      <Button variant="primary" type="submit" busy={busy}>
        Create account
      </Button>
      <p className={styles.signin}>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
