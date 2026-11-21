import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { Button } from "../Button/Button";
import styles from "./Modal.module.css";
export function Modal({
  title,
  children,
  onClose,
  busy = false,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  busy?: boolean;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const element = ref.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`${styles.dialog} ${wide ? styles.wide : ""}`}
      aria-labelledby={id}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
      onContextMenu={(event) => {
        if (event.target === event.currentTarget) {
          event.preventDefault();
          if (!busy) onClose();
        }
      }}
    >
      <section className={styles.panel}>
        <header className={styles.header}>
          <h2 id={id}>{title}</h2>
          <Button
            type="button"
            variant="ghost"
            disabled={busy}
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={22} />
          </Button>
        </header>
        {children}
      </section>
    </dialog>
  );
}
