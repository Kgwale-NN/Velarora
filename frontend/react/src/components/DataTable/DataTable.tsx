import type { ReactNode } from "react";
import { EmptyState } from "../EmptyState/EmptyState";
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
        <table className={styles.table} aria-label="Workspace records">
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
        <EmptyState
          title={empty}
          description="Try another search or add your first record."
        />
      )}
    </div>
  );
}
