import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import styles from "./Tooltip.module.css";

type Props = { label: string; children: ReactNode; enabled?: boolean };
export function Tooltip({ label, children, enabled = true }: Props) {
  const host = useRef<HTMLSpanElement>(null);
  const id = useId();
  const [position, setPosition] = useState<{
    left: number;
    top: number;
  } | null>(null);
  function show() {
    if (!enabled || !window.matchMedia("(hover: hover)").matches) return;
    const rect = host.current?.getBoundingClientRect();
    if (rect)
      setPosition({
        left: rect.right + 20,
        top: Math.max(
          24,
          Math.min(window.innerHeight - 24, rect.top + rect.height / 2),
        ),
      });
  }
  useEffect(() => {
    if (!position) return;
    const close = () => setPosition(null);
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("resize", close);
    window.addEventListener("scroll", close, true);
    document.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", close, true);
      document.removeEventListener("keydown", key);
    };
  }, [position]);
  useEffect(() => setPosition(null), [enabled, label]);
  return (
    <span
      ref={host}
      className={styles.host}
      onMouseEnter={show}
      onMouseLeave={() => setPosition(null)}
      onFocus={show}
      onBlur={() => setPosition(null)}
      aria-describedby={enabled && position ? id : undefined}
    >
      {children}
      {enabled &&
        position &&
        createPortal(
          <span
            id={id}
            role="tooltip"
            className={styles.tooltip}
            style={position}
          >
            {label}
          </span>,
          document.body,
        )}
    </span>
  );
}
