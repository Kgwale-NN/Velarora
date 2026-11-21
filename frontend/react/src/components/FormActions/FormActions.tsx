import type { ReactNode } from "react";
import styles from "./FormActions.module.css";
export function FormActions({ children }: { children: ReactNode }) {
  return <footer className={styles.actions}>{children}</footer>;
}
