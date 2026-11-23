import { PageSkeleton } from "../../components/PageSkeleton/PageSkeleton";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import { useState } from "react";
import { Plus, Pencil, Play, Trash2 } from "lucide-react";
import { useResource, type Row, text } from "../../lib/useResource";
import { api, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import { Modal } from "../../components/Modal/Modal";
import { RecordTable } from "../../components/RecordTable/RecordTable";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import { ScheduleEditor as Editor } from "./ScheduleEditor/ScheduleEditor";
import styles from "./Schedules.module.css";
export function Schedules({ notify }: { notify: Notify }) {
  const r = useResource<Row[]>("/teacher/schedules");
  const [edit, setEdit] = useState<number | null | undefined>(undefined),
    [remove, setRemove] = useState<Row | null>(null),
    [busy, setBusy] = useState(false);
  async function erase() {
    setBusy(true);
    try {
      await api(`/teacher/schedules/${remove!.id}`, json("DELETE"));
      notify("Schedule deleted.");
      setRemove(null);
      r.reload();
    } catch (e) {
      notify(errorText(e), "error");
    } finally {
      setBusy(false);
    }
  }
  async function resume(id: number) {
    try {
      await api(`/teacher/schedules/${id}/resume`, json("POST"));
      notify("Schedule resumed. The exam will start shortly.");
      r.reload();
    } catch (e) {
      notify(errorText(e), "error");
    }
  }
  if (r.loading && !r.data) return <PageSkeleton />;
  return (
    <div className={styles.page}>
      <PageHeading
        title="Your exam schedules"
        description="Plan when classroom monitoring starts and stops."
        action={
          <Button variant="primary" onClick={() => setEdit(null)}>
            <Plus size={17} />
            Add schedule
          </Button>
        }
      />
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <RecordTable
          rows={r.data}
          columns={[
            { key: "name", label: "Exam" },
            { key: "group_name", label: "Classroom" },
            { key: "days_of_week", label: "Days (Mon=0)" },
            { key: "start_time", label: "Start" },
            { key: "end_time", label: "End" },
            {
              key: "runtime_status",
              label: "Status",
              render: (s) =>
                s.runtime_status === "needs_classroom"
                  ? "Needs a classroom"
                  : s.runtime_status === "paused"
                  ? "Paused for this time window"
                  : s.runtime_status === "running"
                    ? "Running"
                    : s.runtime_status === "classroom_in_use"
                      ? "Classroom in use"
                      : s.runtime_status === "disabled"
                        ? "Disabled"
                        : "Scheduled",
            },
            {
              key: "is_active",
              label: "Enabled",
              render: (s) => (s.is_active ? "Yes" : "No"),
            },
            {
              key: "actions",
              label: "Actions",
              render: (s) => (
                <div className={styles.actions}>
                  {s.runtime_status === "paused" && (
                    <Button
                      aria-label="Resume this schedule"
                      onClick={() => void resume(Number(s.id))}
                    >
                      <Play size={17} />
                    </Button>
                  )}
                  <Button
                    aria-label="Edit schedule"
                    onClick={() => setEdit(Number(s.id))}
                  >
                    <Pencil size={17} />
                  </Button>
                  <Button
                    aria-label="Delete schedule"
                    onClick={() => setRemove(s)}
                  >
                    <Trash2 size={17} />
                  </Button>
                </div>
              ),
            },
          ]}
        />
      )}
      {edit !== undefined && (
        <Editor
          id={edit}
          onClose={() => setEdit(undefined)}
          onSave={() => {
            setEdit(undefined);
            r.reload();
          }}
          notify={notify}
        />
      )}
      {remove && (
        <Modal
          title="Delete this schedule?"
          onClose={() => setRemove(null)}
          busy={busy}
        >
          <p>{text(remove.name)} will no longer start automatically.</p>
          <footer>
            <Button onClick={() => setRemove(null)}>Cancel</Button>
            <Button variant="danger" busy={busy} onClick={erase}>
              Delete schedule
            </Button>
          </footer>
        </Modal>
      )}
    </div>
  );
}
