import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bell, X } from "lucide-react";
import { useResource, type Row, text } from "../../lib/useResource";
import { useExamAlarms } from "../ExamAlarms/ExamAlarmsProvider";
import { AlarmList } from "../ExamAlarms/AlarmList";
import { AlarmNotice } from "./AlarmNotice";
import type { Notify } from "../../lib/types";
import styles from "./NotificationBell.module.css";
export function NotificationBell({ notify }: { notify: Notify }) {
  const r = useResource<{
    rows: Row[];
    status: { unread: number; latest: number };
  }>("/teacher/notifications", 5000);
  const alarms = useExamAlarms();
  const [open, setOpen] = useState(false);
  const host = useRef<HTMLDivElement>(null),
    button = useRef<HTMLButtonElement>(null);
  const cursor = useRef<number | null>(null);
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!host.current?.contains(event.target as Node)) setOpen(false);
    };
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", key);
    };
  }, [open]);
  useEffect(() => {
    if (!r.data) return;
    const { status, rows } = r.data;
    if (cursor.current !== null && status.latest > cursor.current) {
      const row = rows.find((n) => Number(n.id) > cursor.current!);
      if (row) notify(`${row.computer} opened ${row.class_name}`);
    }
    cursor.current = status.latest;
  }, [r.data, notify]);
  const count = Math.max(r.data?.status.unread || 0, alarms.rows.length);
  return (
    <div ref={host} className={styles.root}>
      <button
        ref={button}
        type="button"
        className={styles.bell}
        aria-label="Notifications"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? "notification-popover" : undefined}
        onClick={() => setOpen((value) => !value)}
      >
        <Bell size={19} />
        {count > 0 && <span>{Math.min(99, count)}</span>}
      </button>
      {open && (
        <section
          id="notification-popover"
          role="dialog"
          aria-label="Notifications"
          className={styles.popover}
        >
          <header>
            <h2>Notifications</h2>
            <button
              type="button"
              aria-label="Close notifications"
              onClick={() => {
                setOpen(false);
                button.current?.focus();
              }}
            >
              <X size={17} />
            </button>
          </header>
          <div className={styles.body}>
            <h3>Exam alarms</h3>
            <AlarmList />
            {!!r.data?.rows.length && (
              <>
                <h3>Recent alerts</h3>
                {r.data.rows.slice(0, 3).map((row) => (
                  <Link
                    className={styles.alert}
                    key={Number(row.id)}
                    to="/notifications"
                  >
                    <strong>{text(row.computer)}</strong> opened{" "}
                    {text(row.class_name)}
                  </Link>
                ))}
              </>
            )}
          </div>
          <Link className={styles.all} to="/notifications">
            View all notifications
          </Link>
        </section>
      )}
      <AlarmNotice hidden={open || pathname === "/notifications"} />
    </div>
  );
}
