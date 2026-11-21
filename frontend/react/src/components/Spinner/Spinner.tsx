import { Spinner as HeroSpinner } from "@heroui/spinner";
import styles from "./Spinner.module.css";
export function Spinner({ size = "sm" }: { size?: "sm" | "md" }) {
  return (
    <HeroSpinner
      size={size}
      aria-label="Loading"
      classNames={{
        base: styles.base,
        wrapper: `${styles.wrapper} ${size === "md" ? styles.medium : ""}`,
        circle1: styles.circle,
        circle2: styles.second,
      }}
    />
  );
}
