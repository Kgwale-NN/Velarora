import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Spinner } from "../Spinner/Spinner";
import styles from "./AuthProgress.module.css";
export function AuthProgress({ label }: { label: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return createPortal(
    <dialog
      ref={ref}
      className={styles.dialog}
      aria-label={label}
      onCancel={(event) => event.preventDefault()}
    >
      <div role="status" aria-live="polite" className={styles.content}>
        <Spinner size="md" />
        <strong>{label}</strong>
        <span>Please wait a moment.</span>
      </div>
    </dialog>,
    document.body,
  );
}
