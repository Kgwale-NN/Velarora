import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { Bell, X, VolumeX } from "lucide-react";
import { useExamAlarms } from "../ExamAlarms/ExamAlarmsProvider";
import { Button } from "../Button/Button";
import { text } from "../../lib/useResource";
import { computerLabel } from "../../lib/computerLabel";
import styles from "./AlarmNotice.module.css";
export function AlarmNotice({ hidden = false }: { hidden?: boolean }) {
  const alarms = useExamAlarms();
  const seen = useRef(new Set<number>());
  const [id, setId] = useState<number | null>(null);
  useEffect(() => {
    const fresh = alarms.rows.filter(
      (row) => !seen.current.has(Number(row.id)) && !row.stopped_at,
    );
    alarms.rows.forEach((row) => seen.current.add(Number(row.id)));
    if (fresh.length) setId(Number(fresh[0].id));
  }, [alarms.rows]);
  const alarm = alarms.rows.find((row) => Number(row.id) === id);
  if (!alarm || hidden) return null;
  return createPortal(
    <section
      className={styles.notice}
      data-exam-alarm-notice="true"
      role="alert"
      aria-label="Exam alarm notification"
    >
      <header>
        <Bell size={17} />
        <strong>Exam alarm</strong>
        <button
          type="button"
          aria-label="Dismiss alarm notification"
          onClick={() => setId(null)}
        >
          <X size={17} />
        </button>
      </header>
      <p>
        <strong>{computerLabel(alarm.computer_id, alarm.computer || alarm.computer_name)}</strong> opened{" "}
        {text(alarm.app_name || alarm.process_name || alarm.app)}
      </p>
      <small>{text(alarm.classroom || "Your exam")}</small>
      <footer>
        <Button
          variant="primary"
          disabled={!!alarm.stopped_at || alarms.busy !== null}
          busy={alarms.busy === id}
          onClick={() => void alarms.stop(Number(alarm.id))}
        >
          <VolumeX size={14} />
          {alarm.stopped_at ? "Stop requested" : "Stop alarm"}
        </Button>
        <Link to="/notifications" onClick={() => setId(null)}>
          View details
        </Link>
      </footer>
    </section>,
    document.body,
  );
}
