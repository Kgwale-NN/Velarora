import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bell, X } from "lucide-react";
import { type Row, text } from "../../lib/useResource";
import { AlarmList } from "../ExamAlarms/AlarmList";
import { AlarmNotice } from "./AlarmNotice";
import type { Notify } from "../../lib/types";
import styles from "./NotificationBell.module.css";
type Data = { rows: Row[]; status: { unread: number; latest: number } };
export function NotificationBell({ notify, data }: { notify: Notify; data: Data | null }) {
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
    if (!data) return;
    const { status, rows } = data;
    if (cursor.current !== null && status.latest > cursor.current) {
      const row = rows.find((n) => Number(n.id) > cursor.current!);
      if (row) notify(`${row.computer} opened ${row.class_name}`);
    }
    cursor.current = status.latest;
  }, [data, notify]);
  const count = data?.status.unread || 0;
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
        {count > 0 && <span>{count > 99 ? "99+" : count}</span>}
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
            {!!data?.rows.length && (
              <>
                <h3>Recent alerts</h3>
                {data.rows.slice(0, 3).map((row) => (
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
