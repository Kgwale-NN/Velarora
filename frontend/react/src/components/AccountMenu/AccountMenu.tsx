import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { Link, useLocation } from "react-router-dom";
import { LogOut, UserRound } from "lucide-react";
import { Tooltip } from "../Tooltip/Tooltip";
import styles from "./AccountMenu.module.css";
type Props = {
  name: string;
  role: string;
  compact?: boolean;
  onLogout: () => void;
};
export function AccountMenu({ name, compact = false, onLogout }: Props) {
  const [open, setOpen] = useState(false),
    [position, setPosition] = useState<{
      left: number;
      bottom?: number;
      top?: number;
    }>({ left: 12, bottom: 60 });
  const trigger = useRef<HTMLButtonElement>(null),
    popup = useRef<HTMLDivElement>(null);
  const id = useId(),
    location = useLocation();
  const initials = name.trim().charAt(0).toUpperCase() || "?";
  const theme = `${styles.theme} ${styles.light}`;
  function close(restore = false) {
    setOpen(false);
    if (restore) trigger.current?.focus();
  }
  function show() {
    const rect = trigger.current?.getBoundingClientRect();
    if (!rect) return;
    const width = Math.min(260, window.innerWidth - 24);
    const left = Math.max(
      12,
      Math.min(rect.left, window.innerWidth - width - 12),
    );
    setPosition(
      rect.top >= 230
        ? { left, bottom: window.innerHeight - rect.top + 10 }
        : { left, top: Math.min(rect.bottom + 10, window.innerHeight - 230) },
    );
    setOpen(true);
  }
  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    if (!open) return;
    popup.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
    const outside = (event: Event) => {
      const target = event.target as Node;
      if (trigger.current?.contains(target) || popup.current?.contains(target))
        return;
      if (event.type === "contextmenu") event.preventDefault();
      setOpen(false);
    };
    const resize = () => setOpen(false);
    const scroll = (event: Event) => {
      if (!popup.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("contextmenu", outside);
    window.addEventListener("resize", resize);
    window.addEventListener("scroll", scroll, true);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("contextmenu", outside);
      window.removeEventListener("resize", resize);
      window.removeEventListener("scroll", scroll, true);
    };
  }, [open]);
  function keyboard(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(true);
      return;
    }
    if (event.key === "Tab") {
      setOpen(false);
      return;
    }
    const keys = ["ArrowDown", "ArrowUp", "Home", "End"];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const items = Array.from(
      popup.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') || [],
    );
    const current = items.indexOf(document.activeElement as HTMLElement);
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? items.length - 1
          : event.key === "ArrowDown"
            ? (current + 1) % items.length
            : (current - 1 + items.length) % items.length;
    items[next]?.focus();
  }
  return (
    <div className={`${theme} ${styles.root}`}>
      <Tooltip label={name} enabled={compact && !open}>
        <button
          ref={trigger}
          id={id}
          type="button"
          className={`${styles.trigger} ${compact ? styles.compact : ""}`}
          aria-label="Open account menu"
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={open ? id + "-popup" : undefined}
          onClick={() => (open ? close(true) : show())}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault();
              if (!open) show();
              else
                popup.current
                  ?.querySelector<HTMLElement>('[role="menuitem"]')
                  ?.focus();
            }
          }}
        >
          <span className={styles.avatar} aria-hidden="true">
            {initials}
          </span>
          <span className={styles.name}>{name}</span>
        </button>
      </Tooltip>
      {open &&
        createPortal(
          <div
            ref={popup}
            id={id + "-popup"}
            role="menu"
            aria-labelledby={id}
            className={`${theme} ${styles.menu}`}
            style={position}
            onKeyDown={keyboard}
          >
            <div className={styles.header}>
              <span className={styles.avatar} aria-hidden="true">
                {initials.toUpperCase()}
              </span>
              <div className={styles.identity}>
                <strong>{name}</strong>
              </div>
            </div>
            <Link
              to="/profile"
              role="menuitem"
              className={styles.item}
              onClick={() => close()}
            >
              <UserRound size={17} />
              <span>Profile</span>
            </Link>
            <button
              type="button"
              role="menuitem"
              className={styles.item}
              onClick={() => {
                close();
                onLogout();
              }}
            >
              <LogOut size={17} />
              <span>Log out</span>
            </button>
          </div>,
          document.body,
        )}
    </div>
  );
}
