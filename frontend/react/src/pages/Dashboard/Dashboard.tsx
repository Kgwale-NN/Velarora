import { useRef, useState } from "react";
import { Monitor, Play, Square, Wifi, Bell, Expand } from "lucide-react";
import { useExamAlarms } from "../../components/ExamAlarms/ExamAlarmsProvider";
import { useResource, text, type Row } from "../../lib/useResource";
import { api, json, errorText } from "../../lib/api";
import type { Notify, LiveFrame } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import { Select } from "../../components/Select/Select";
import { Check } from "../../components/Check/Check";
import { Panel } from "../../components/Panel/Panel";
import { StatCard } from "../../components/StatCard/StatCard";
import { Modal } from "../../components/Modal/Modal";
import {
  ComputerScreen,
  screenSource,
} from "../../components/ComputerScreen/ComputerScreen";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./Dashboard.module.css";
type Live = {
  running: boolean;
  owned: boolean;
  stopping: boolean;
  frames: LiveFrame[];
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
    [busy, setBusy] = useState(false),
    [opened, setOpened] = useState<string | null>(null);
  const selected = rooms.data
    ? rooms.data.some((r) => String(r.id) === room)
      ? room
      : String(rooms.data[0]?.id || "")
    : room;
  const classroom = rooms.data?.find((r) => String(r.id) === selected);
  const live = useResource<Live>(
    selected ? `/classrooms/${selected}/live` : null,
    2000,
  );
  const alarms = useExamAlarms();
  const frames = live.data?.frames || [],
    alarmRows = alarms.rows;
  const activeAlarms = alarmRows.filter(
    (a) => !a.stopped_at || !!a.audio_active,
  );
  const visible = !!live.data?.running && (overview || !!live.data.owned);
  const online = frames.filter((f) => f.online).length;
  const status = live.data?.stopping
    ? "Stopping"
    : live.data?.running
      ? live.data.owned || overview
        ? "Monitoring"
        : "In use"
      : "Stopped";
  const names = [
    ...new Set([
      ...(live.data?.computers || []).map((c) => text(c.name)),
      ...frames.map((f) => f.name),
    ]),
  ];
  const expanded = frames.find((f) => f.name === opened);
  const image = useRef<HTMLImageElement>(null);
  async function command(path: string, payload: unknown = {}) {
    setBusy(true);
    try {
      await api(path, json("POST", payload));
      notify(
        path.endsWith("/start")
          ? "Exam started."
          : path.includes("/alarms/")
            ? "Alarm stop requested."
            : "Exam stopped.",
      );
      live.reload();
      alarms.reload();
    } catch (e) {
      notify(errorText(e), "error");
    } finally {
      setBusy(false);
    }
  }
  function refresh() {
    rooms.reload();
    live.reload();
    alarms.reload();
  }
  async function fullscreen() {
    if (!image.current?.requestFullscreen) {
      notify("Fullscreen is not available in this browser.", "error");
      return;
    }
    try {
      await image.current.requestFullscreen();
    } catch (e) {
      notify(errorText(e), "error");
    }
  }
  return (
    <div className={styles.page}>
      <header className={styles.heading}>
        <div>
          <p className={styles.eyebrow}>CLASSROOM WORKSPACE</p>
          <h1>{overview ? "Classroom overview" : "Exam dashboard"}</h1>
          <p className={styles.subtitle}>
            {overview
              ? "A live view of classroom monitoring across your school."
              : "Choose a classroom, start your exam, and keep every screen in view."}
          </p>
        </div>
      </header>
      <Panel>
        <div className={styles.toolbar}>
          <div className={styles.classroom}>
            <Select
              label="Classroom"
              value={selected}
              disabled={busy || rooms.loading || !rooms.data?.length}
              onChange={(value) => {
                setRoom(value);
                setOpened(null);
                localStorage.setItem("velarora.classroom", value);
              }}
              options={
                rooms.data?.length
                  ? rooms.data.map((r) => ({
                      value: Number(r.id),
                      label: text(r.name),
                    }))
                  : [
                      {
                        value: "",
                        label: rooms.loading
                          ? "Loading classrooms…"
                          : "No classrooms available",
                      },
                    ]
              }
            />
          </div>
          <span
            className={styles.status}
            data-running={!!live.data?.running}
            role="status"
          >
            <span />
            {live.loading ? "Checking status" : status}
          </span>
          {!overview && (
            <div className={styles.examControls}>
              <Button
                variant="primary"
                disabled={
                  !selected ||
                  !classroom?.computer_count ||
                  live.loading ||
                  !!live.error ||
                  !!live.data?.running
                }
                busy={busy}
                onClick={() =>
                  command("/teacher/exam/start", {
                    classroom_id: Number(selected),
                  })
                }
              >
                <Play size={14} />
                Start exam
              </Button>
              <Button
                disabled={
                  !live.data?.running ||
                  !live.data?.owned ||
                  !!live.data?.stopping
                }
                busy={busy}
                onClick={() =>
                  command("/teacher/exam/stop", {
                    classroom_id: Number(selected),
                  })
                }
              >
                <Square size={14} />
                Stop exam
              </Button>
            </div>
          )}
        </div>
      </Panel>
      <div className={styles.stats}>
        <StatCard
          label="Classroom PCs"
          value={classroom ? Number(classroom.computer_count) : "—"}
          icon={<Monitor />}
          note={classroom ? text(classroom.name) : "Choose a classroom"}
        />
        <StatCard
          label="Online PCs"
          value={visible ? online : "—"}
          icon={<Wifi />}
          note={visible ? "Recent screen captures" : "Checked during an exam"}
        />
        <StatCard
          label={overview ? "Screen previews" : "Active alarms"}
          value={
            overview
              ? frames.length
              : alarms.loading || alarms.error
                ? "—"
                : activeAlarms.length
          }
          icon={overview ? <Monitor /> : <Bell />}
          note={overview ? "Captured classroom screens" : "Across your exams"}
        />
      </div>
      <ResourceState
        loading={rooms.loading || live.loading}
        error={rooms.error || live.error}
        retry={refresh}
      />
      <div className={styles.content}>
        <div className={styles.screens}>
          <div className={styles.sectionHeading}>
            <div>
              <h2>
                Live screens <span>{names.length}</span>
              </h2>
              <p>
                {visible
                  ? "Select a screen for a closer look."
                  : "Screen previews appear when monitoring begins."}
              </p>
            </div>
            <Check
              label="Show detections"
              checked={annotations}
              onChange={(e) => setAnnotations(e.target.checked)}
            />
          </div>
          {names.length > 0 ? (
            <div className={styles.grid}>
              {names.map((name) => (
                <ComputerScreen
                  key={name}
                  name={name}
                  frame={frames.find((f) => f.name === name)}
                  annotations={annotations}
                  onOpen={() => setOpened(name)}
                />
              ))}
            </div>
          ) : (
            !live.loading &&
            !rooms.loading && (
              <Panel>
                <div className={styles.empty}>
                  <span className={styles.emptyIcon}>
                    <Monitor size={28} strokeWidth={1.5} />
                  </span>
                  <h3>
                    {live.data?.running
                      ? "Waiting for screen captures"
                      : selected
                        ? "Ready when you are"
                        : "Choose your classroom"}
                  </h3>
                  <p>
                    {live.data?.running && !live.data.owned && !overview
                      ? "Another teacher is monitoring this classroom."
                      : classroom && !classroom.computer_count
                        ? "This classroom has no PCs yet. Ask your administrator to add them."
                        : !rooms.data?.length
                          ? "Ask your administrator to set up a classroom and its PCs."
                          : "Start your exam to see the student computers here."}
                  </p>
                </div>
              </Panel>
            )
          )}
        </div>
      </div>
      {expanded && (
        <Modal title={expanded.name} wide onClose={() => setOpened(null)}>
          <div className={styles.previewToolbar}>
            <span className={styles.muted}>
              {expanded.online
                ? "Live classroom screen"
                : "Last captured screen · PC offline"}
            </span>
            <Button onClick={fullscreen}>
              <Expand size={15} />
              Full screen
            </Button>
          </div>
          <img
            ref={image}
            className={styles.fullImage}
            src={screenSource(expanded, annotations)}
            alt={"Expanded screen of " + expanded.name}
          />
        </Modal>
      )}
    </div>
  );
}
