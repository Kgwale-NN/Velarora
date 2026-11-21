import { VolumeX } from "lucide-react";
import { useExamAlarms } from "./ExamAlarmsProvider";
import { text } from "../../lib/useResource";
import { Button } from "../Button/Button";
import { ResourceState } from "../ResourceState/ResourceState";
import styles from "./AlarmList.module.css";
export function AlarmList() {
  const alarms = useExamAlarms();
  return (
    <div className={styles.list}>
      <ResourceState
        loading={alarms.loading}
        error={alarms.error}
        retry={alarms.reload}
      />
      {alarms.rows.map((alarm) => (
        <article key={Number(alarm.id)} className={styles.item}>
          <div className={styles.heading}>
            <strong>{text(alarm.computer || alarm.computer_name)}</strong>
            <span>{alarm.stopped_at ? "Stopping" : "Alarm active"}</span>
          </div>
          <p>{text(alarm.app_name || alarm.process_name || alarm.app)}</p>
          <small>{text(alarm.classroom || "Your exam")}</small>
          <Button
            variant="primary"
            disabled={!!alarm.stopped_at || alarms.busy !== null}
            busy={alarms.busy === Number(alarm.id)}
            onClick={() => void alarms.stop(Number(alarm.id))}
          >
            <VolumeX size={15} />
            {alarm.stopped_at ? "Stop requested" : "Stop alarm"}
          </Button>
        </article>
      ))}
      {!alarms.loading && !alarms.error && !alarms.rows.length && (
        <p className={styles.empty}>No active exam alarms.</p>
      )}
    </div>
  );
}
