import { useEffect, useState, type ReactNode } from "react";
import { Navbar, NavbarContent } from "@heroui/navbar";
import styles from "./WorkspaceNavbar.module.css";
export function WorkspaceNavbar({ children }: { children: ReactNode }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const update = (event?: Event) => {
      const target = event?.target;
      if (
        target instanceof HTMLElement &&
        target.hasAttribute("data-workspace-scroll")
      )
        setScrolled(target.scrollTop > 4);
      else if (!event || target === document) setScrolled(window.scrollY > 4);
    };
    update();
    document.addEventListener("scroll", update, {
      passive: true,
      capture: true,
    });
    return () => document.removeEventListener("scroll", update, true);
  }, []);
  return (
    <Navbar
      aria-label="Workspace navigation"
      position="sticky"
      maxWidth="full"
      isBlurred
      classNames={{
        base: `${styles.navbar} ${scrolled ? styles.scrolled : ""}`,
        wrapper: styles.wrapper,
      }}
    >
      <NavbarContent as="div" className={styles.content} justify="start">
        {children}
      </NavbarContent>
    </Navbar>
  );
}
