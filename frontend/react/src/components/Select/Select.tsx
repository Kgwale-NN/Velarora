import { useId, type SelectHTMLAttributes } from "react";
import styles from "./Select.module.css";
type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: { value: string | number; label: string }[];
};
export function Select({ label, options, ...props }: Props) {
  const id = useId();
  return (
    <div className={styles.field}>
      <label htmlFor={id}>{label}</label>
      <select id={id} {...props}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
