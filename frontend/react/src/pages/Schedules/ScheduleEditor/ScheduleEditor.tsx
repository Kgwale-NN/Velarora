import { useState } from "react";
import { api, json, errorText } from "../../../lib/api";
import type { Notify } from "../../../lib/types";
import { text, type Row } from "../../../lib/useResource";
import { Input } from "../../../components/Input/Input";
import { Button } from "../../../components/Button/Button";
import { useResource } from "../../../lib/useResource";
import { Select } from "../../../components/Select/Select";
import { Check } from "../../../components/Check/Check";
import { Modal } from "../../../components/Modal/Modal";
import { ResourceState } from "../../../components/ResourceState/ResourceState";
import styles from "./ScheduleEditor.module.css";
export function ScheduleEditor({
  id,
  onClose,
  onSave,
  notify,
}: {
  id: number | null;
  onClose: () => void;
  onSave: () => void;
  notify: Notify;
}) {
  const r = useResource<{
    groups: Row[];
    models: Row[];
    active: Row | null;
    classes: Record<string, Row[]>;
    schedule: Row | null;
  }>("/teacher/schedule-options" + (id ? "?schedule_id=" + id : ""));
  const [form, setForm] = useState<Row | null>(null),
    [busy, setBusy] = useState(false);
  const s = r.data?.schedule;
  const f = form || {
    name: s?.name || "",
    group_id: s?.group_id || r.data?.groups[0]?.id || "",
    model_id: s?.model_id || "",
    start: s?.start_time || "09:00",
    end: s?.end_time || "10:00",
    days: String(s?.days_of_week ?? "0").split(","),
    active: s ? !!s.is_active : true,
    custom: !!s?.use_custom_notify_classes,
    notify_ids: s?.notify_class_ids || [],
  };
  const change = (key: string, value: unknown) =>
    setForm({ ...f, [key]: value });
  const days = f.days as string[],
    ids = f.notify_ids as number[];
  return (
    <Modal
      title={id ? "Edit exam schedule" : "New exam schedule"}
      onClose={onClose}
      busy={busy}
    >
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <form
          className={styles.form}
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            try {
              await api(
                "/teacher/schedules" + (id ? "/" + id : ""),
                json(id ? "PUT" : "POST", {
                  ...f,
                  group_id: Number(f.group_id),
                  model_id: f.model_id ? Number(f.model_id) : null,
                }),
              );
              notify("Schedule saved.");
              onSave();
            } catch (e) {
              notify(errorText(e), "error");
            } finally {
              setBusy(false);
            }
          }}
        >
          <Input
            label="Exam name"
            placeholder="Exam name"
            value={text(f.name)}
            onChange={(e) => change("name", e.target.value)}
            required
          />
          <Select
            label="Classroom"
            value={text(f.group_id)}
            onChange={(e) => change("group_id", e.target.value)}
            options={r.data.groups.map((g) => ({
              value: Number(g.id),
              label: text(g.name),
            }))}
          />
          <Select
            label="Model"
            value={text(f.model_id)}
            onChange={(e) =>
              setForm({ ...f, model_id: e.target.value, notify_ids: [] })
            }
            options={[
              { value: "", label: "Use active model" },
              ...r.data.models.map((m) => ({
                value: Number(m.id),
                label: text(m.name),
              })),
            ]}
          />
          <div className={styles.actions}>
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d, i) => (
              <Check
                key={d}
                label={d}
                checked={days.includes(String(i))}
                onChange={(e) =>
                  change(
                    "days",
                    e.target.checked
                      ? [...days, String(i)]
                      : days.filter((v) => v !== String(i)),
                  )
                }
              />
            ))}
          </div>
          <div className={styles.split}>
            <Input
              label="Start time"
              type="time"
              value={text(f.start)}
              onChange={(e) => change("start", e.target.value)}
              required
            />
            <Input
              label="End time"
              type="time"
              value={text(f.end)}
              onChange={(e) => change("end", e.target.value)}
              required
            />
          </div>
          <Check
            label="Schedule enabled"
            checked={!!f.active}
            onChange={(e) => change("active", e.target.checked)}
          />
          <Check
            label="Use custom detected-class alerts"
            checked={!!f.custom}
            onChange={(e) => change("custom", e.target.checked)}
          />
          {!!f.custom &&
            (r.data.classes[String(f.model_id || r.data.active?.id)] || []).map(
              (c) => (
                <Check
                  key={Number(c.id)}
                  label={text(c.name)}
                  checked={ids.includes(Number(c.id))}
                  onChange={(e) =>
                    change(
                      "notify_ids",
                      e.target.checked
                        ? [...ids, Number(c.id)]
                        : ids.filter((v) => v !== c.id),
                    )
                  }
                />
              ),
            )}
          <p className={styles.muted}>
            Times use the server computer's clock. The classroom starts and
            stops automatically on the selected days.
          </p>
          <Button type="submit" busy={busy}>
            Save schedule
          </Button>
        </form>
      )}
    </Modal>
  );
}
