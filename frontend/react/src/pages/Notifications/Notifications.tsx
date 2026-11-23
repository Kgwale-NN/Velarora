import { PageSkeleton } from "../../components/PageSkeleton/PageSkeleton";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import { AlarmList } from "../../components/ExamAlarms/AlarmList";
import { useState } from "react";
import { useResource, type Row, text } from "../../lib/useResource";
import { api, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { Snapshot } from "../../components/Snapshot/Snapshot";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./Notifications.module.css";
export function Notifications({
  notify,
  onRead,
}: {
  notify: Notify;
  onRead: (id?: number) => void;
}) {
  const r = useResource<{ rows: Row[]; status: { unread: number } }>(
    "/teacher/notifications",
    5000,
  );
  const [shot, setShot] = useState<number | null>(null);
  async function read(id?: number) {
    try {
      await api("/teacher/notifications/read", json("POST", { id }));
      r.setData((current) => {
        if (!current) return current;
        if (id === undefined) {
          return {
            ...current,
            rows: current.rows.map((notification) => ({ ...notification, is_read: 1 })),
            status: { ...current.status, unread: 0 },
          };
        }
        const target = current.rows.find((notification) => Number(notification.id) === id);
        if (!target || target.is_read) return current;
        return {
          ...current,
          rows: current.rows.map((notification) =>
            Number(notification.id) === id ? { ...notification, is_read: 1 } : notification,
          ),
          status: { ...current.status, unread: Math.max(0, current.status.unread - 1) },
        };
      });
      onRead(id);
    } catch (e) {
      notify(errorText(e), "error");
    }
  }
  if (r.loading && !r.data) return <PageSkeleton />;
  return (
    <div className={styles.page}>
      <PageHeading
        title="Notifications"
        description={`${r.data?.status.unread || 0} unread alerts. Review exam alarms and recent activity.`}
        action={<Button onClick={() => read()}>Mark all as read</Button>}
      />
      <ResourceState {...r} retry={r.reload} />
      <Panel title="Active exam alarms">
        <AlarmList />
      </Panel>
      <Panel>
        {r.data?.rows.map((n) => (
          <div className={styles.item} key={Number(n.id)}>
            <div className={styles.heading}>
              <strong>
                {text(n.computer)} opened {text(n.class_name)}
              </strong>
              <span className={styles.muted}>{text(n.created_at)}</span>
            </div>
            <p>
              {text(n.student)} · {n.is_read ? "Read" : "Unread"}
            </p>
            <div className={styles.actions}>
              {!!n.has_frame && (
                <Button onClick={() => setShot(Number(n.event_id))}>
                  View screenshot
                </Button>
              )}
              {!n.is_read && (
                <Button onClick={() => read(Number(n.id))}>Mark as read</Button>
              )}
            </div>
          </div>
        ))}
        {!r.loading && !r.data?.rows.length && (
          <p className={styles.empty}>No alerts yet.</p>
        )}
      </Panel>
      {shot !== null && <Snapshot id={shot} onClose={() => setShot(null)} />}
    </div>
  );
}
