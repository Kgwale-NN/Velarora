import { useEffect, useRef, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { ScrollShadow } from "@heroui/scroll-shadow";
import styles from "./WorkspaceScroll.module.css";
export function WorkspaceScroll({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = 0;
  }, [pathname]);
  return (
    <ScrollShadow
      ref={ref}
      size={40}
      className={styles.scroll}
      data-workspace-scroll="true"
      role="region"
      aria-label="Page content"
      tabIndex={0}
    >
      {children}
    </ScrollShadow>
  );
}
