import type { ReactNode } from "react";
import { Inbox } from "lucide-react";
import styles from "./DataTable.module.css";
export interface Column<T> {
  label: string;
  key: string;
  render: (row: T) => ReactNode;
}
export function DataTable<T extends { id: number }>({
  columns,
  rows,
  empty = "No matching records",
  busy = false,
}: {
  columns: Column<T>[];
  rows: T[];
  empty?: string;
  busy?: boolean;
}) {
  return (
    <div className={styles.frame} aria-busy={busy}>
      <div className={styles.scroll}>
        <table className={styles.table}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} scope="col">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {busy
              ? Array.from({ length: 4 }, (_, i) => (
                  <tr key={i}>
                    {columns.map((c) => (
                      <td key={c.key}>
                        <div className={styles.skeleton} />
                      </td>
                    ))}
                  </tr>
                ))
              : rows.map((row) => (
                  <tr key={row.id}>
                    {columns.map((column) => (
                      <td key={column.key}>{column.render(row)}</td>
                    ))}
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
      {!busy && !rows.length && (
        <div className={styles.empty}>
          <Inbox size={30} />
          <strong>{empty}</strong>
          <span>Try another search or add your first record.</span>
        </div>
      )}
    </div>
  );
}
