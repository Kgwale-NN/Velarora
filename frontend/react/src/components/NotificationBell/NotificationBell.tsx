import { useEffect, useRef } from "react";
import { NavLink } from "react-router-dom";
import { Bell } from "lucide-react";
import { useResource, type Row } from "../../lib/useResource";
import type { Notify } from "../../lib/types";
import styles from "./NotificationBell.module.css";
export function NotificationBell({ notify }: { notify: Notify }) {
  const r = useResource<{
    rows: Row[];
    status: { unread: number; latest: number };
  }>("/teacher/notifications", 5000);
  const cursor = useRef<number | null>(null);
  useEffect(() => {
    if (!r.data) return;
    const { status, rows } = r.data;
    if (cursor.current !== null && status.latest > cursor.current) {
      const row = rows.find((n) => Number(n.id) > cursor.current!);
      if (row) notify(`${row.computer} opened ${row.class_name}`);
    }
    cursor.current = status.latest;
  }, [r.data, notify]);
  return (
    <NavLink
      className={styles.bell}
      to="/notifications"
      aria-label="Notifications"
    >
      <Bell size={20} />
      {!!r.data?.status.unread && (
        <span>{Math.min(99, r.data.status.unread)}</span>
      )}
    </NavLink>
  );
}
