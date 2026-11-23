import styles from "./BrandSplash.module.css";

export function BrandSplash({ exiting = false }: { exiting?: boolean }) {
  return (
    <div
      className={`${styles.screen} ${exiting ? styles.exiting : ""}`}
      role="status"
      aria-label="Loading Velarora"
    >
      <svg
        className={styles.mark}
        viewBox="0 0 56 56"
        fill="none"
        aria-hidden="true"
      >
        <path className={styles.left} d="M10 10 28 46" />
        <path className={styles.right} d="M46 10 28 46" />
      </svg>
    </div>
  );
}
