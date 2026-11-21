import { Monitor } from "lucide-react";
import { ActionLink } from "../../components/ActionLink/ActionLink";
import styles from "./Welcome.module.css";
export function Welcome() {
  return (
    <div className={styles.page}>
      <img
        className={styles.background}
        src="/design-assets/computer-lab2.jpg"
        alt=""
        aria-hidden="true"
        fetchPriority="high"
      />
      <div className={styles.shade} />
      <div className={styles.container}>
        <header className={styles.header}>
          <span className={styles.mark}>
            <Monitor size={20} strokeWidth={1.5} />
          </span>
          <span className={styles.brand}>Velarora</span>
        </header>
        <main className={styles.main}>
          <div className={styles.copy}>
            <p className={styles.eyebrow}>CLASSROOM EXAM MONITORING</p>
            <h1>
              Your classroom.
              <br />
              In clear view.
            </h1>
            <p className={styles.description}>
              Monitor classroom computers, manage exam times, and respond to
              alerts from one place.
            </p>
            <div className={styles.actions}>
              <ActionLink to="/login">Log in</ActionLink>
              <ActionLink to="/signup" variant="glass">
                Create teacher account
              </ActionLink>
            </div>
          </div>
        </main>
        <footer className={styles.footer}>
          Built for teachers and invigilators.
        </footer>
      </div>
    </div>
  );
}
