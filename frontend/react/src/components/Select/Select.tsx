import { useId, type SelectHTMLAttributes } from "react";
import styles from "./Select.module.css";
type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: { value: string | number; label: string }[];
};
export function Select({ label, options, ...props }: Props) {
  const id = useId();
  return (
    <label className={styles.field} htmlFor={id}>
      {label}
      <select id={id} {...props}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
