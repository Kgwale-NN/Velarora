import { Tooltip } from "../Tooltip/Tooltip";
import styles from "./SidebarToggle.module.css";
type Props = { open: boolean; onClick: () => void };
export function SidebarToggle({ open, onClick }: Props) {
  const label = open ? "Close sidebar" : "Open sidebar";
  return (
    <Tooltip label={label}>
      <button
        type="button"
        className={styles.toggle}
        aria-label={label}
        aria-expanded={open}
        aria-controls="workspace-sidebar"
        onClick={onClick}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          {!open && (
            <path
              d="M7 4H9V20H7A4 4 0 0 1 3 16V8A4 4 0 0 1 7 4Z"
              fill="currentColor"
              fillOpacity=".12"
              stroke="none"
            />
          )}
          <rect x="3" y="4" width="18" height="16" rx="4" />
          <path d="M9 4V20" />
        </svg>
      </button>
    </Tooltip>
  );
}
