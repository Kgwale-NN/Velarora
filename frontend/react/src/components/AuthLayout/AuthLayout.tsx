import type { FormEventHandler, ReactNode } from "react";
import styles from "./AuthLayout.module.css";
export function AuthLayout({
  title,
  children,
  onSubmit,
  aside,
}: {
  title: string;
  children: ReactNode;
  onSubmit: FormEventHandler<HTMLFormElement>;
  aside?: ReactNode;
}) {
  return (
    <main className={styles.page}>
      <img
        className={styles.background}
        src="/design-assets/computer-lab2.jpg"
        alt=""
        aria-hidden="true"
        fetchPriority="high"
      />
      <form className={styles.card} onSubmit={onSubmit}>
        <span className={styles.brand}>Velarora</span>
        <h1>{title}</h1>
        {children}
      </form>
      {aside}
    </main>
  );
}
