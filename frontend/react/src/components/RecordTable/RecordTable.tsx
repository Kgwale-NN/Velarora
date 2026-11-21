import type { ReactNode } from "react";
import styles from "./RecordTable.module.css";
import { text, type Row } from "../../lib/useResource";
export type Column = {
  key: string;
  label: string;
  render?: (row: Row) => ReactNode;
};
export function RecordTable({
  rows,
  columns,
  label = "Records",
}: {
  rows: Row[];
  columns: Column[];
  label?: string;
}) {
  return (
    <div className={styles.scroll}>
      <table aria-label={label}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={text(row.id ?? row.event_id ?? i)}>
              {columns.map((c) => (
                <td key={c.key}>
                  {c.render ? c.render(row) : text(row[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p className={styles.empty}>No records yet.</p>}
    </div>
  );
}
