import { Monitor, Expand, ScanEye } from "lucide-react";
import type { LiveFrame } from "../../lib/types";
import { Panel } from "../Panel/Panel";
import styles from "./ComputerScreen.module.css";
export function screenSource(frame: LiveFrame, annotations: boolean) {
  const source = (annotations ? frame.annotated : frame.raw) || frame.raw;
  return source.startsWith("data:")
    ? source
    : "data:image/jpeg;base64," + source;
}
export function ComputerScreen({
  name,
  frame,
  annotations,
  onOpen,
}: {
  name: string;
  frame?: LiveFrame;
  annotations: boolean;
  onOpen: () => void;
}) {
  return (
    <Panel>
      <header className={styles.header}>
        <span className={styles.name}>
          <Monitor size={15} />
          {name}
        </span>
        <span className={styles.status} data-online={!!frame?.online}>
          {frame ? (frame.online ? "Online" : "Offline") : "Waiting"}
        </span>
      </header>
      <button
        type="button"
        className={styles.preview}
        onClick={onOpen}
        disabled={!frame}
        aria-label={"View screen of " + name}
      >
        {frame ? (
          <>
            <img
              src={screenSource(frame, annotations)}
              alt={"Live screen of " + name}
            />
            <span className={styles.expand}>
              <Expand size={16} />
            </span>
          </>
        ) : (
          <span className={styles.waiting}>
            <Monitor size={27} />
            <span>Waiting for a screen capture</span>
          </span>
        )}
      </button>
      <footer className={styles.footer}>
        <span>
          <ScanEye size={13} />
          {frame
            ? `${frame.detections.length} detection${frame.detections.length === 1 ? "" : "s"}`
            : "No capture yet"}
        </span>
        <span>
          {frame?.online
            ? "Live preview"
            : frame
              ? "Last capture"
              : "Connecting"}
        </span>
      </footer>
    </Panel>
  );
}
