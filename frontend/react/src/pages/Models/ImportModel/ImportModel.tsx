import { useState } from "react";
import { api, json, errorText } from "../../../lib/api";
import type { Notify } from "../../../lib/types";
import { Input } from "../../../components/Input/Input";
import { Button } from "../../../components/Button/Button";
import { Modal } from "../../../components/Modal/Modal";
import styles from "./ImportModel.module.css";
export function ImportModel({
  notify,
  onClose,
  onSave,
}: {
  notify: Notify;
  onClose: () => void;
  onSave: () => void;
}) {
  const [path, setPath] = useState(""),
    [busy, setBusy] = useState(false);
  async function upload(file: File) {
    setBusy(true);
    try {
      const data = new FormData();
      data.append("file", file);
      await api("/admin/models/upload", { method: "POST", body: data });
      notify("Model imported.");
      onSave();
    } catch (e) {
      notify(errorText(e), "error");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Import model" onClose={onClose} busy={busy}>
      <div className={styles.form}>
        <p>
          Upload trusted ONNX or PT weights. PT weights are converted to ONNX
          before use.
        </p>
        <Input
          label="Model file"
          type="file"
          accept=".onnx,.pt"
          disabled={busy}
          onChange={(e) => {
            if (e.target.files?.[0]) void upload(e.target.files[0]);
          }}
        />
        <p className={styles.muted}>Or use a file already on this server.</p>
        <Input
          label="Server file path"
          placeholder="C:\models\best.onnx"
          value={path}
          onChange={(e) => setPath(e.target.value)}
        />
        <Button
          busy={busy}
          disabled={!path}
          onClick={async () => {
            setBusy(true);
            try {
              await api("/admin/models/import-path", json("POST", { path }));
              notify("Model imported.");
              onSave();
            } catch (e) {
              notify(errorText(e), "error");
            } finally {
              setBusy(false);
            }
          }}
        >
          Import from path
        </Button>
      </div>
    </Modal>
  );
}
