import { CheckCircle2, AlertCircle, X } from "lucide-react";
import { useEffect } from "react";
import styles from "./Toast.module.css";
export interface ToastMessage {
  id: number;
  text: string;
  kind: "success" | "error";
}
export function Toast({
  message,
  onDismiss,
}: {
  message: ToastMessage | null;
  onDismiss: () => void;
}) {
  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(onDismiss, 6500);
    return () => window.clearTimeout(timer);
  }, [message, onDismiss]);
  return (
    message && (
      <div
        className={styles.toast}
        role={message.kind === "error" ? "alert" : "status"}
      >
        {message.kind === "error" ? (
          <AlertCircle size={22} />
        ) : (
          <CheckCircle2 size={22} />
        )}
        <span>{message.text}</span>
        <button onClick={onDismiss} aria-label="Dismiss notification">
          <X size={18} />
        </button>
      </div>
    )
  );
}
