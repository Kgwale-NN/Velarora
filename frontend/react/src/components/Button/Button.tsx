import type { ButtonHTMLAttributes } from "react";
import { Spinner } from "../Spinner/Spinner";
import styles from "./Button.module.css";
type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  busy?: boolean;
};
export function Button({
  children,
  variant,
  type = "button",
  busy = false,
  disabled,
  className = "",
  ...props
}: Props) {
  return (
    <button
      {...props}
      type={type}
      disabled={disabled || busy}
      aria-busy={busy}
      className={`${styles.button} ${styles[variant ?? (type === "submit" ? "primary" : "secondary")]} ${className}`}
    >
      {busy && <Spinner />} {children}
    </button>
  );
}
