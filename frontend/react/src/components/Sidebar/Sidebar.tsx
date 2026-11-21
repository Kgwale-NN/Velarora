import { useEffect, useRef } from "react";
import { NavLink } from "react-router-dom";
import { ScrollShadow } from "@heroui/scroll-shadow";
import { X, type LucideIcon } from "lucide-react";
import { Button } from "../Button/Button";
import { Tooltip } from "../Tooltip/Tooltip";
import { AccountMenu } from "../AccountMenu/AccountMenu";
import styles from "./Sidebar.module.css";
type Props = {
  name: string;
  role: string;
  home: string;
  links: readonly (readonly [string, string, LucideIcon])[];
  collapsed: boolean;
  mobile: boolean;
  open: boolean;
  onClose: () => void;
  onLogout: () => void;
};
export function Sidebar({
  name,
  role,
  home,
  links,
  collapsed,
  mobile,
  open,
  onClose,
  onLogout,
}: Props) {
  const element = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!mobile || !open) return;
    const previous = document.activeElement as HTMLElement | null;
    element.current
      ?.querySelector<HTMLButtonElement>('button[aria-label="Close menu"]')
      ?.focus();
    return () => previous?.focus();
  }, [mobile, open]);
  return (
    <>
      <aside
        ref={element}
        id="workspace-sidebar"
        className={`${styles.sidebar} ${styles.light} ${collapsed ? styles.collapsed : ""} ${open ? styles.open : ""}`}
        aria-label="Workspace sidebar"
        aria-hidden={mobile && !open ? true : undefined}
        inert={mobile && !open}
        onKeyDown={(event) => {
          if (!mobile || !open) return;
          if (event.key === "Escape") {
            event.preventDefault();
            onClose();
          }
          if (event.key === "Tab") {
            const items = Array.from(
              element.current?.querySelectorAll<HTMLElement>(
                "a[href],button:not(:disabled)",
              ) || [],
            );
            if (!items.length) return;
            const first = items[0],
              last = items[items.length - 1];
            if (event.shiftKey && document.activeElement === first) {
              event.preventDefault();
              last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
              event.preventDefault();
              first.focus();
            }
          }
        }}
      >
        <div className={styles.top}>
          <NavLink
            to={home}
            className={styles.brand}
            title="Velarora"
            aria-label="Velarora home"
          >
            <span className={styles.brandFull}>
              Velarora<small>EXAM WORKSPACE</small>
            </span>
            <span className={styles.brandMark} aria-hidden="true">
              V
            </span>
          </NavLink>
          <Button
            className={styles.close}
            variant="ghost"
            aria-label="Close menu"
            onClick={onClose}
          >
            <X size={20} />
          </Button>
        </div>
        <p className={styles.caption}>
          {role === "admin" ? "ADMINISTRATION" : "TEACHER WORKSPACE"}
        </p>
        <ScrollShadow size={40} hideScrollBar className={styles.scrollArea}>
          <nav className={styles.navigation} aria-label="Main menu">
            {links.map(([label, url, Icon]) => (
              <Tooltip key={url} label={label} enabled={collapsed}>
                <NavLink
                  to={url}
                  aria-label={label}
                  className={({ isActive }) =>
                    `${styles.link} ${isActive ? styles.active : ""}`
                  }
                >
                  <Icon size={18} aria-hidden="true" />
                  <span className={styles.label}>{label}</span>
                </NavLink>
              </Tooltip>
            ))}
          </nav>
        </ScrollShadow>
        <div className={styles.bottom}>
          <AccountMenu
            name={name}
            role={role}
            compact={collapsed}
            onLogout={onLogout}
          />
        </div>
      </aside>
      {mobile && open && (
        <button
          className={styles.scrim}
          aria-label="Close navigation"
          onClick={onClose}
        />
      )}
    </>
  );
}
