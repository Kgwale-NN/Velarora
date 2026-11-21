import { useId, type FormEventHandler, type ReactNode } from "react";
import styles from "./AuthLayout.module.css";
export function AuthLayout({
  title,
  children,
  description,
  onSubmit,
  aside,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  onSubmit: FormEventHandler<HTMLFormElement>;
  aside?: ReactNode;
}) {
  const heading = useId();
  return (
    <main className={styles.page}>
      <section className={styles.formSide}>
        <form
          className={styles.card}
          onSubmit={onSubmit}
          aria-labelledby={heading}
        >
          <header className={styles.heading}>
            <span className={styles.brand}>Velarora</span>
            <h1 id={heading}>{title}</h1>
            {description && <p>{description}</p>}
          </header>
          {children}
        </form>
      </section>
      <div className={styles.visual} aria-hidden="true">
        <img
          className={styles.background}
          src="/design-assets/computer-lab2.jpg"
          alt=""
          aria-hidden="true"
          fetchPriority="high"
        />
      </div>
      {aside}
    </main>
  );
}
