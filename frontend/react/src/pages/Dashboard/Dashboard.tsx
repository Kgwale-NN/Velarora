import { useState } from "react";
import { Monitor, Play, Square, RefreshCw, VolumeX } from "lucide-react";
import { useResource, text, type Row } from "../../lib/useResource";
import { api, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import { Select } from "../../components/Select/Select";
import { Check } from "../../components/Check/Check";
import { Panel } from "../../components/Panel/Panel";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./Dashboard.module.css";
type Frame = {
  id: number;
  name: string;
  raw: string;
  annotated: string;
  online: boolean;
  detections: unknown[];
};
type Live = {
  running: boolean;
  owned: boolean;
  stopping: boolean;
  frames: Frame[];
  logs: string[];
  computers: Row[];
};
export function Dashboard({
  notify,
  overview = false,
}: {
  notify: Notify;
  overview?: boolean;
}) {
  const rooms = useResource<Row[]>("/classrooms");
  const [room, setRoom] = useState(
      localStorage.getItem("velarora.classroom") || "",
    ),
    [annotations, setAnnotations] = useState(true),
    [busy, setBusy] = useState(false);
  const selected = room || String(rooms.data?.[0]?.id || "");
  const live = useResource<Live>(`/classrooms/${selected || 0}/live`, 2000);
  const alarms = useResource<Row[]>(
    overview ? "/classrooms" : "/teacher/alarms",
    3000,
  );
  async function command(path: string, payload: unknown = {}) {
    setBusy(true);
    try {
      await api(path, json("POST", payload));
      notify("Command sent.");
      live.reload();
      alarms.reload();
    } catch (e) {
      notify(errorText(e), "error");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className={styles.page}>
      <header className={styles.heading}>
        <div>
          <h1>{overview ? "Classroom overview" : "Exam dashboard"}</h1>
          <p className={styles.muted}>
            {overview
              ? "View classroom monitoring across the school."
              : "Choose your classroom and watch the student PCs during your exam."}
          </p>
        </div>
        <Button onClick={live.reload}>
          <RefreshCw size={17} />
          Refresh
        </Button>
      </header>
      <Panel>
        <div className={styles.toolbar}>
          <Select
            label="Classroom"
            value={selected}
            onChange={(e) => {
              setRoom(e.target.value);
              localStorage.setItem("velarora.classroom", e.target.value);
            }}
            options={(rooms.data || []).map((r) => ({
              value: Number(r.id),
              label: text(r.name),
            }))}
          />
          <span className={styles.badge}>
            {live.data?.stopping
              ? "Stopping"
              : live.data?.running
                ? "Monitoring"
                : "Stopped"}
          </span>
          {!overview && (
            <>
              <Button
                variant="primary"
                disabled={!selected || !!live.data?.running}
                busy={busy}
                onClick={() =>
                  command("/teacher/exam/start", {
                    classroom_id: Number(selected),
                  })
                }
              >
                <Play size={17} />
                Start exam
              </Button>
              <Button
                variant="danger"
                disabled={!live.data?.running || !live.data?.owned}
                busy={busy}
                onClick={() =>
                  command("/teacher/exam/stop", {
                    classroom_id: Number(selected),
                  })
                }
              >
                <Square size={17} />
                Stop exam
              </Button>
            </>
          )}
          <Check
            label="Show detections"
            checked={annotations}
            onChange={(e) => setAnnotations(e.target.checked)}
          />
        </div>
      </Panel>
      <ResourceState
        loading={live.loading || rooms.loading}
        error={live.error || rooms.error}
        retry={() => {
          rooms.reload();
          live.reload();
        }}
      />
      {!overview && alarms.error && (
        <ResourceState
          loading={false}
          error={alarms.error}
          retry={alarms.reload}
        />
      )}
      {!overview &&
        (alarms.data || []).map((a) => (
          <Panel
            key={Number(a.id)}
            title={text(a.computer_name || a.computer || "Workstation alarm")}
          >
            <p>
              {text(a.app_name || a.process_name || a.app)} —{" "}
              {a.stopped_at
                ? "Waiting for the workstation to confirm silence."
                : "An unapproved app was opened."}
            </p>
            <Button
              disabled={!!a.stopped_at}
              busy={busy}
              onClick={() => command(`/teacher/alarms/${a.id}/stop`)}
            >
              <VolumeX size={18} />
              Stop alarm
            </Button>
          </Panel>
        ))}
      <div className={styles.grid}>
        {live.data?.frames.map((f) => (
          <Panel key={f.name} title={f.name}>
            <span className={styles.badge}>
              {f.online ? "Online" : "Offline"}
            </span>
            <img
              className={styles.image}
              src={
                (annotations ? f.annotated : f.raw).startsWith("data:")
                  ? annotations
                    ? f.annotated
                    : f.raw
                  : "data:image/jpeg;base64," +
                    (annotations ? f.annotated : f.raw)
              }
              alt={`Live screen of ${f.name}`}
            />
            <p>{f.detections.length} detection(s)</p>
          </Panel>
        ))}
      </div>
      {!live.loading && !live.data?.frames.length && (
        <Panel>
          <div className={styles.empty}>
            <Monitor size={36} />
            <p>
              {live.data?.running && !live.data.owned && !overview
                ? "Another teacher is monitoring this classroom."
                : "Screen previews appear here when your exam starts and captures arrive."}
            </p>
          </div>
        </Panel>
      )}
      <Panel title="Monitoring activity">
        <pre className={styles.logs}>
          {[...(live.data?.logs || [])].reverse().join("\n") ||
            "No activity yet."}
        </pre>
      </Panel>
    </div>
  );
}
