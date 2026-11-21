import { Inbox } from "lucide-react";
import styles from "./EmptyState.module.css";
export function EmptyState({
  title = "No records yet",
  description = "Records will appear here when they are available.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className={styles.empty}>
      <span className={styles.icon}>
        <Inbox size={22} strokeWidth={1.5} />
      </span>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}
