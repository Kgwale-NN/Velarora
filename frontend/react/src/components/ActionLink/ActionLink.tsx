import { Link, type LinkProps } from "react-router-dom";
import styles from "./ActionLink.module.css";
type Props = LinkProps & { variant?: "light" | "glass" };
export function ActionLink({
  variant = "light",
  className = "",
  ...props
}: Props) {
  return (
    <Link
      {...props}
      className={`${styles.link} ${styles[variant]} ${className}`}
    />
  );
}
