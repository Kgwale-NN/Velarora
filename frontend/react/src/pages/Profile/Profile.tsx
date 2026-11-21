import { FormActions } from "../../components/FormActions/FormActions";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import { useEffect, useState, type FormEvent } from "react";
import { api, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { useResource } from "../../lib/useResource";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./Profile.module.css";
export function Profile({
  notify,
  onUpdated,
}: {
  notify: Notify;
  onUpdated: () => void;
}) {
  const r = useResource<{ username: string; email: string; role: string }>(
    "/profile",
  );
  const [name, setName] = useState(""),
    [current, setCurrent] = useState(""),
    [password, setPassword] = useState(""),
    [confirm, setConfirm] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (r.data) setName(r.data.username);
  }, [r.data]);
  async function save(e: FormEvent, changePassword = false) {
    e.preventDefault();
    if (changePassword && password !== confirm) {
      notify("The passwords do not match.", "error");
      return;
    }
    setBusy(true);
    try {
      await api(
        "/profile" + (changePassword ? "/password" : ""),
        json(
          "PUT",
          changePassword ? { current, password } : { username: name },
        ),
      );
      notify(changePassword ? "Password updated." : "Profile updated.");
      if (changePassword) {
        setCurrent("");
        setPassword("");
        setConfirm("");
      } else onUpdated();
    } catch (e) {
      notify(errorText(e), "error");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className={styles.page}>
      <PageHeading
        title="Your profile"
        description="Manage your display name and password."
      />
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <div className={styles.split}>
          <Panel title="Account details">
            <form className={styles.form} onSubmit={save}>
              <Input
                label="Display name"
                placeholder="Your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={100}
                required
              />
              <Input
                label="Email address"
                type="email"
                value={r.data.email || ""}
                readOnly
                hint="Your sign-in email is managed by your administrator."
              />
              <span className={styles.badge}>
                {r.data.role === "admin" ? "Administrator" : "Teacher"}
              </span>
              <FormActions>
                <Button type="submit" busy={busy}>
                  Save profile
                </Button>
              </FormActions>
            </form>
          </Panel>
          <Panel title="Change password">
            <form className={styles.form} onSubmit={(e) => save(e, true)}>
              <Input
                label="Current password"
                placeholder="Current password"
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                required
              />
              <Input
                label="New password"
                placeholder="New password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={12}
                required
                hint="At least 12 characters. Start with a capital letter and include a number and symbol."
              />
              <Input
                label="Confirm password"
                placeholder="Repeat new password"
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
              />
              <FormActions>
                <Button type="submit" busy={busy}>
                  Update password
                </Button>
              </FormActions>
            </form>
          </Panel>
        </div>
      )}
    </div>
  );
}
