import { useEffect, useState, type FormEvent } from "react";
import { api, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { useResource } from "../../lib/useResource";
import { Select } from "../../components/Select/Select";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./AppRules.module.css";
export function AppRules({ notify }: { notify: Notify }) {
  const r = useResource<{ mode: string; processes: string[] }>(
    "/teacher/policy",
  );
  const [mode, setMode] = useState("blocklist"),
    [processes, setProcesses] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (r.data) {
      setMode(r.data.mode);
      setProcesses(r.data.processes.join("\n"));
    }
  }, [r.data]);
  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api(
        "/teacher/policy",
        json("PUT", {
          mode,
          processes: processes
            .split(/[\n,]+/)
            .map((s) => s.trim())
            .filter(Boolean),
        }),
      );
      notify("Application rules saved.");
    } catch (e) {
      notify(errorText(e), "error");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className={styles.page}>
      <h1>Application rules</h1>
      <p className={styles.muted}>
        These rules belong to you and apply to your exams. The workstation agent
        reports the app used on each PC.
      </p>
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <Panel title="Your exam policy">
          <form className={styles.form} onSubmit={save}>
            <Select
              label="Policy"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              options={[
                { value: "blocklist", label: "Block these apps" },
                { value: "allowlist", label: "Allow only these apps" },
              ]}
            />
            <label htmlFor="processes">Application file names</label>
            <textarea
              id="processes"
              className={styles.fieldarea}
              placeholder={"notepad.exe\nChatGPT.exe"}
              value={processes}
              onChange={(e) => setProcesses(e.target.value)}
            />
            <p className={styles.muted}>
              Write one executable name per line, such as notepad.exe. A
              forbidden app starts a continuous alarm on that student PC. Only
              you can stop your exam alarms from the dashboard.
            </p>
            <Button type="submit" busy={busy}>
              Save rules
            </Button>
          </form>
        </Panel>
      )}
    </div>
  );
}
