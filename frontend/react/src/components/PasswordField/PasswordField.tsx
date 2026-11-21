import { useState } from "react";
import type { InputHTMLAttributes } from "react";
import { Eye, EyeOff, LockKeyhole } from "lucide-react";
import { Input } from "../Input/Input";
import styles from "./PasswordField.module.css";
export function PasswordField({
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className={styles.field}>
      <Input
        {...props}
        label={label}
        type={visible ? "text" : "password"}
        icon={<LockKeyhole size={18} />}
      />
      <button
        type="button"
        aria-label={(visible ? "Hide " : "Show ") + label.toLowerCase()}
        aria-pressed={visible}
        onClick={() => setVisible(!visible)}
      >
        {visible ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div>
  );
}
