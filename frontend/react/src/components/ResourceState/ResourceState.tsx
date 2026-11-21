import {
  PageSkeleton,
  type SkeletonVariant,
} from "../PageSkeleton/PageSkeleton";
import { Button } from "../Button/Button";
import styles from "./ResourceState.module.css";
export function ResourceState({
  loading,
  error,
  retry,
  variant = "table",
}: {
  loading: boolean;
  error: string;
  retry: () => void;
  variant?: SkeletonVariant;
}) {
  return (
    <>
      {loading && <PageSkeleton variant={variant} heading={false} />}
      {error && (
        <div className={styles.error} role="alert">
          {error}
          <Button onClick={retry}>Try again</Button>
        </div>
      )}
    </>
  );
}
