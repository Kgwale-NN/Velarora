import type { InputHTMLAttributes } from "react";
import styles from "./Check.module.css";
export function Check({
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className={styles.check}>
      <input type="checkbox" {...props} />
      <span>{label}</span>
    </label>
  );
}
