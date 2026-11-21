import { useLocation } from "react-router-dom";
import styles from "./PageSkeleton.module.css";
export type SkeletonVariant =
  | "dashboard"
  | "users"
  | "classrooms"
  | "table"
  | "analytics"
  | "form"
  | "profile"
  | "settings"
  | "list"
  | "models"
  | "workstations";
const layouts: Record<string, SkeletonVariant> = {
  dashboard: "dashboard",
  "classroom-overview": "dashboard",
  users: "users",
  classrooms: "classrooms",
  history: "table",
  analytics: "analytics",
  reports: "table",
  schedules: "table",
  "app-rules": "form",
  notifications: "list",
  profile: "profile",
  settings: "settings",
  models: "models",
  "model-alert-rules": "list",
  audit: "table",
  workstations: "workstations",
  login: "form",
};
function Block({
  kind = "line",
}: {
  kind?: "line" | "title" | "field" | "screen" | "button";
}) {
  return <span className={`${styles.block} ${styles[kind]}`} />;
}
function Fields({ count = 3 }: { count?: number }) {
  return (
    <div className={styles.fields}>
      {Array.from({ length: count }, (_, i) => (
        <div className={styles.fieldGroup} key={i}>
          <Block />
          <Block kind="field" />
        </div>
      ))}
    </div>
  );
}
function Stats({ count = 3 }: { count?: number }) {
  return (
    <div
      className={styles.stats}
      style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
    >
      {Array.from({ length: count }, (_, i) => (
        <div className={styles.card} key={i}>
          <Block />
          <Block kind="title" />
          <Block />
        </div>
      ))}
    </div>
  );
}
function Table({ columns = 6 }: { columns?: number }) {
  return (
    <div className={styles.table}>
      {Array.from({ length: 5 }, (_, i) => (
        <div
          className={styles.row}
          key={i}
          style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
        >
          {Array.from({ length: columns }, (_, j) => (
            <Block key={j} />
          ))}
        </div>
      ))}
    </div>
  );
}
function Form({
  count = 3,
  columns = false,
  textarea = false,
}: {
  count?: number;
  columns?: boolean;
  textarea?: boolean;
}) {
  return (
    <div className={`${styles.card} ${columns ? "" : styles.form}`}>
      <Block kind="title" />
      <Fields count={count} />
      {textarea && <Block kind="screen" />}
      <div className={styles.actions}>
        <Block kind="button" />
      </div>
    </div>
  );
}
export function PageSkeleton({
  variant,
  heading = true,
}: {
  variant?: SkeletonVariant;
  heading?: boolean;
}) {
  const { pathname } = useLocation();
  const layout =
    variant ||
    layouts[pathname.split("/").filter(Boolean).at(-1) || ""] ||
    "table";
  let content;
  switch (layout) {
    case "dashboard":
      content = (
        <>
          <div className={styles.card}>
            <Fields count={3} />
          </div>
          <Stats />
          <div className={styles.two}>
            {[0, 1].map((i) => (
              <div className={styles.card} key={i}>
                <Block />
                <Block kind="screen" />
              </div>
            ))}
          </div>
        </>
      );
      break;
    case "users":
    case "classrooms":
      content = (
        <>
          <Stats count={layout === "users" ? 4 : 3} />
          <Fields />
          <Table />
        </>
      );
      break;
    case "analytics":
      content = (
        <>
          <div className={styles.card}>
            <Fields count={4} />
          </div>
          <Stats />
          <div className={styles.two}>
            {[0, 1].map((i) => (
              <div className={styles.card} key={i}>
                <Block />
                <Block kind="screen" />
              </div>
            ))}
          </div>
          <Table />
        </>
      );
      break;
    case "profile":
      content = (
        <div className={styles.two}>
          <Form count={2} />
          <Form count={3} />
        </div>
      );
      break;
    case "settings":
      content = (
        <>
          {[5, 5, 4, 8, 1].map((count, i) => (
            <Form key={i} count={count} columns />
          ))}
        </>
      );
      break;
    case "form":
      content = pathname.endsWith("/app-rules") ? (
        <Form count={1} textarea />
      ) : (
        <Form />
      );
      break;
    case "list":
      content = (
        <>
          {[0, 1, 2].map((i) => (
            <div className={styles.card} key={i}>
              <Block kind="title" />
              <Block />
              <Block />
              <div className={styles.actions}>
                <Block kind="button" />
              </div>
            </div>
          ))}
        </>
      );
      break;
    case "models":
      content = (
        <>
          <div className={styles.card}>
            <Block kind="title" />
            <Block />
            <Block />
          </div>
          <Table />
        </>
      );
      break;
    case "workstations":
      content = (
        <>
          <Form count={2} />
          <Table />
        </>
      );
      break;
    default:
      content = (
        <>
          <Fields />
          <Table />
        </>
      );
  }
  return (
    <div
      className={styles.layout}
      role="status"
      aria-label="Loading page content"
      aria-busy="true"
      data-skeleton-layout={layout}
    >
      <div className={styles.visual} aria-hidden="true">
        {heading && (
          <div className={styles.heading}>
            <Block kind="title" />
            <Block />
          </div>
        )}
        {content}
      </div>
    </div>
  );
}
