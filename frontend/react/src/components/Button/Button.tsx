import type { ButtonHTMLAttributes } from "react";
import { LoaderCircle } from "lucide-react";
import styles from "./Button.module.css";
type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  busy?: boolean;
};
export function Button({
  children,
  variant = "secondary",
  busy = false,
  disabled,
  className = "",
  ...props
}: Props) {
  return (
    <button
      {...props}
      disabled={disabled || busy}
      aria-busy={busy}
      className={`${styles.button} ${styles[variant]} ${className}`}
    >
      {busy && <LoaderCircle className={styles.spinner} size={17} />} {children}
    </button>
  );
}
