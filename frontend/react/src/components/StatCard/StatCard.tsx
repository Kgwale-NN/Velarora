import type { ReactNode } from "react";
import styles from "./StatCard.module.css";
export function StatCard({
  label,
  value,
  icon,
  note,
}: {
  label: string;
  value: number | string;
  icon: ReactNode;
  note: string;
}) {
  return (
    <article className={styles.card}>
      <div className={styles.top}>
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}
