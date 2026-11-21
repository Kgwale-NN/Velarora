import { useId, type InputHTMLAttributes, type ReactNode } from "react";
import styles from "./Input.module.css";
type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  icon?: ReactNode;
  hint?: string;
};
export function Input({ label, icon, hint, id: provided, ...props }: Props) {
  const generated = useId();
  const id = provided || generated;
  return (
    <div className={styles.field}>
      <label htmlFor={id}>{label}</label>
      <div className={styles.control}>
        {icon}
        <input
          {...props}
          id={id}
          aria-describedby={hint ? id + "-hint" : undefined}
        />
      </div>
      {hint && <small id={id + "-hint"}>{hint}</small>}
    </div>
  );
}
