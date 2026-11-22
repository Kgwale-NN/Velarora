import { PageSkeleton } from "../../components/PageSkeleton/PageSkeleton";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import { useState } from "react";
import { Download } from "lucide-react";
import { useResource, text, type Row } from "../../lib/useResource";
import { api, json, saveBlob, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { Input } from "../../components/Input/Input";
import { Select } from "../../components/Select/Select";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { RecordTable } from "../../components/RecordTable/RecordTable";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./Workstations.module.css";
export function Workstations({ notify }: { notify: Notify }) {
  const r = useResource<{ computers: Row[]; groups: Row[]; agents: Row[] }>(
    "/admin/workstations",
    10000,
  );
  const [pc, setPc] = useState(""),
    [url, setUrl] = useState(location.origin),
    [busy, setBusy] = useState(false);
  const [name, setName] = useState(""), [classroom, setClassroom] = useState(""),
    [registering, setRegistering] = useState(false);
  if (r.loading && !r.data) return <PageSkeleton />;
  return (
    <div className={styles.page}>
      <PageHeading
        title="Workstation setup"
        description="Connect classroom PCs and manage their workstation agents."
      />
      <ResourceState {...r} retry={r.reload} />
      <Panel title="Add a campus PC">
        <p className={styles.muted}>
          For a PC at another location, use the portable Windows agent. It sends
          that PC’s screens over HTTPS to this server. Your home desktop must stay on.
        </p>
        <form className={styles.form} onSubmit={async (e) => {
          e.preventDefault(); setRegistering(true);
          try {
            const added = await api<{id: number}>("/admin/workstations/computers",
              json("POST", {name, classroom_id: Number(classroom)}));
            await r.reload(); setPc(String(added.id)); setName("");
            notify("PC added. Download its configuration below.");
          } catch (error) { notify(errorText(error), "error"); }
          finally { setRegistering(false); }
        }}>
          <Input label="PC name" placeholder="Campus Demo PC" value={name}
            onChange={(e) => setName(e.target.value)} required maxLength={100} />
          <Select label="Classroom" value={classroom} onChange={setClassroom} required
            options={[{value: "", label: "Choose a classroom"}, ...(r.data?.groups || []).map(g =>
              ({value: Number(g.id), label: text(g.name)}))]} />
          <Button type="submit" busy={registering}>Add campus PC</Button>
        </form>
      </Panel>
      <Panel title="Download a PC configuration">
        <p>
          Campus PCs use the portable agent for screen capture, app names and alarms.
          Existing Veyon PCs keep their current screen capture connection.
        </p>
        <form
          className={styles.form}
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            try {
              const config = await api(
                "/admin/workstations/provision",
                json("POST", { computer_id: Number(pc), server_url: url }),
              );
              saveBlob(
                new Blob([JSON.stringify(config, null, 2)], {
                  type: "application/json",
                }),
                `velarora-pc-${pc}.json`,
              );
              notify("Configuration downloaded. Copy it beside the portable app and rename it agent.json.");
              r.reload();
            } catch (e) {
              notify(errorText(e), "error");
            } finally {
              setBusy(false);
            }
          }}
        >
          <Select
            label="Computer"
            value={pc}
            onChange={(value) => setPc(value)}
            required
            options={[
              { value: "", label: "Choose a computer" },
              ...(r.data?.computers || []).map((c) => ({
                value: Number(c.id),
                label: text(c.name),
              })),
            ]}
          />
          <Input
            label="Server address"
            type="url"
            placeholder="https://school-server:8080"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            hint="Use HTTPS on the classroom network. localhost is only for testing this PC."
          />
          <p className={styles.muted}>
            Downloading a new configuration replaces this PC's previous key.
            Keep the file on that PC only.
          </p>
          <Button busy={busy} type="submit">
            <Download size={17} />
            Download agent configuration
          </Button>
        </form>
      </Panel>
      <Panel title="Classroom big-screen links">
        {r.data?.groups.map((g) => (
          <p key={Number(g.id)}>
            <a
              className={styles.link}
              href={"/admin/dashboard?classroom=" + g.id}
            >
              {text(g.name)}
            </a>
            <br />
            <small>
              {location.origin}/admin/dashboard?classroom={text(g.id)}
            </small>
          </p>
        ))}
      </Panel>
      <Panel title="Agent connections">
        <RecordTable
          rows={r.data?.agents || []}
          columns={[
            { key: "name", label: "Computer" },
            { key: "last_seen", label: "Last connected" },
            { key: "last_app", label: "Foreground app" },
            { key: "enabled", label: "Enabled" },
          ]}
        />
      </Panel>
    </div>
  );
}
