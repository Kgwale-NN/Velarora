import { MonitorUp, Square, BellOff } from "lucide-react";
import type { Notify } from "../../lib/types";
import { Button } from "../Button/Button";
import { Panel } from "../Panel/Panel";
import { useBrowserMonitor } from "./useBrowserMonitor";
import styles from "./BrowserMonitor.module.css";

export function BrowserMonitor({ notify }: { notify: Notify }) {
  const monitor = useBrowserMonitor(notify);
  return (
    <Panel title="Share this PC’s screen">
      <div className={styles.body}>
        <p className={styles.description}>
          Run your demonstration from this browser. Choose{" "}
          <strong>Entire screen</strong>, then open Notepad. Keep this dashboard
          open in its tab.
        </p>
        <div className={styles.controls}>
          <Button
            variant="primary"
            busy={monitor.busy && !monitor.running}
            disabled={monitor.running}
            onClick={monitor.start}
          >
            <MonitorUp size={16} /> Share screen
          </Button>
          {monitor.running && (
            <Button onClick={monitor.stop}>
              <Square size={16} /> End sharing
            </Button>
          )}
          {monitor.alarm && (
            <Button
              variant="danger"
              busy={monitor.busy}
              onClick={monitor.silence}
            >
              <BellOff size={16} /> Stop browser alarm
            </Button>
          )}
        </div>
        <p className={styles.status} role="status">
          {monitor.status}
          {monitor.running && ` · ${monitor.model}`}
        </p>
        <canvas
          ref={monitor.canvas}
          hidden={!monitor.running}
          className={styles.screen}
          aria-label="Shared screen with AI detection boxes"
        />
        {monitor.result && monitor.running && (
          <p className={styles.result}>
            {monitor.result.detections.length
              ? monitor.result.detections
                  .map((d) => `${d.name} (${Math.round(d.conf * 100)}%)`)
                  .join(" · ")
              : "No recognised application in the latest picture."}
          </p>
        )}
        <p className={styles.note}>
          Only the screen you approve is captured. Pictures are sent to Velarora
          and saved in your exam history. Your administrator must activate an
          ONNX model and enable its alert rule. Browser sound needs your
          speakers on and can be stopped by closing or muting the page. This is
          a demonstration, not the protected Windows workstation alarm.
        </p>
      </div>
    </Panel>
  );
}
