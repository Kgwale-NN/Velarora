import { Spinner as HeroSpinner } from "@heroui/spinner";
import styles from "./Spinner.module.css";
export function Spinner() {
  return (
    <HeroSpinner
      size="sm"
      aria-label="Loading"
      classNames={{
        base: styles.base,
        wrapper: styles.wrapper,
        circle1: styles.circle,
        circle2: styles.second,
      }}
    />
  );
}
