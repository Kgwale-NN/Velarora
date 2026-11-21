import { Button } from "../Button/Button";
import styles from "./ResourceState.module.css";
export function ResourceState({
  loading,
  error,
  retry,
}: {
  loading: boolean;
  error: string;
  retry: () => void;
}) {
  return (
    <>
      {loading && (
        <div
          className={styles.skeleton}
          role="status"
          aria-label="Loading records"
        />
      )}
      {error && (
        <div className={styles.error} role="alert">
          {error}
          <Button onClick={retry}>Try again</Button>
        </div>
      )}
    </>
  );
}
