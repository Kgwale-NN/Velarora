import { CheckCircle2, AlertCircle, X } from "lucide-react";
import { useEffect, useState } from "react";
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
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (!message || paused) return;
    const timer = window.setTimeout(onDismiss, 6500);
    return () => window.clearTimeout(timer);
  }, [message, onDismiss, paused]);
  return (
    message && (
      <div
        className={styles.toast}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onFocus={() => setPaused(true)}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget))
            setPaused(false);
        }}
        role={message.kind === "error" ? "alert" : "status"}
      >
        {message.kind === "error" ? (
          <AlertCircle size={22} />
        ) : (
          <CheckCircle2 size={22} />
        )}
        <span>{message.text}</span>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss notification"
        >
          <X size={18} />
        </button>
      </div>
    )
  );
}
