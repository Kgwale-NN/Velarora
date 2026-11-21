import styles from "./Bars.module.css";
export function Bars({ rows }: { rows: { label: string; value: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className={styles.chart}>
      {rows.map((r, i) => (
        <div key={i}>
          <span>{r.label}</span>
          <div className={styles.track}>
            <div style={{ width: `${(r.value / max) * 100}%` }} />
          </div>
          <strong>{r.value}</strong>
        </div>
      ))}
      {!rows.length && <p>No activity recorded yet.</p>}
    </div>
  );
}
