import { useState } from "react";
import { api, json, errorText } from "../../../lib/api";
import type { Notify } from "../../../lib/types";
import { text, type Row } from "../../../lib/useResource";
import { Input } from "../../../components/Input/Input";
import { Button } from "../../../components/Button/Button";
import { Select } from "../../../components/Select/Select";
import { Check } from "../../../components/Check/Check";
import { Panel } from "../../../components/Panel/Panel";
import styles from "./TrainingForm.module.css";
export function TrainingForm({
  models,
  bases,
  notify,
  onStart,
}: {
  models: Row[];
  bases: string[];
  notify: Notify;
  onStart: () => void;
}) {
  const [path, setPath] = useState(""),
    [analysis, setAnalysis] = useState<Row | null>(null),
    [busy, setBusy] = useState(false),
    [form, setForm] = useState({
      base_model: "yolov5n.pt",
      name: "model_" + Date.now(),
      epochs: 30,
      imgsz: 640,
      batch: 4,
      source_id: "",
      learning_rate: 0.001,
      freeze_backbone: false,
      extend_classes: false,
    });
  async function analyse(file?: File) {
    setBusy(true);
    try {
      let data: Row;
      if (file) {
        const body = new FormData();
        body.append("file", file);
        data = await api<Row>("/admin/datasets/upload", {
          method: "POST",
          body,
        });
      } else
        data = await api<Row>("/admin/datasets/path", json("POST", { path }));
      setAnalysis(data);
      setPath(text(data.dataset_dir));
      notify("Dataset checked. Review the classes before training.");
    } catch (e) {
      notify(errorText(e), "error");
      setAnalysis(null);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel title="Train a model">
      <form
        className={styles.form}
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await api(
              "/admin/training",
              json("POST", {
                ...form,
                dataset_path: path,
                source_id: form.source_id ? Number(form.source_id) : null,
              }),
            );
            notify("Training started. You may leave this page and return.");
            onStart();
          } catch (e) {
            notify(errorText(e), "error");
          } finally {
            setBusy(false);
          }
        }}
      >
        <h3>1. Choose your labelled dataset</h3>
        <Input
          label="Dataset ZIP"
          type="file"
          accept=".zip"
          disabled={busy}
          onChange={(e) => {
            if (e.target.files?.[0]) void analyse(e.target.files[0]);
          }}
        />
        <div className={styles.toolbar}>
          <Input
            label="Dataset server folder"
            placeholder="C:\datasets\notepad"
            value={path}
            onChange={(e) => {
              setPath(e.target.value);
              setAnalysis(null);
            }}
          />
          <Button
            type="button"
            busy={busy}
            disabled={!path}
            onClick={() => analyse()}
          >
            Analyse dataset
          </Button>
        </div>
        {analysis && (
          <>
            <p>
              {text(analysis.nc)} classes:{" "}
              {((analysis.names as string[]) || []).join(", ")}
            </p>
            <p className={styles.muted}>
              {JSON.stringify(analysis.warnings || [])}
            </p>
            <h3>2. Training settings</h3>
            <div className={styles.grid}>
              <Input
                label="Model name"
                placeholder="Model name"
                value={form.name}
                pattern="[A-Za-z0-9_-]+"
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
              <Select
                label="Base model"
                value={form.base_model}
                onChange={(value) => setForm({ ...form, base_model: value })}
                options={bases.map((b) => ({ value: b, label: b }))}
              />
              {(["epochs", "imgsz", "batch"] as const).map((k) => (
                <Input
                  key={k}
                  label={
                    k === "imgsz"
                      ? "Image size"
                      : k === "epochs"
                        ? "Epochs"
                        : "Batch size"
                  }
                  type="number"
                  min={k === "imgsz" ? 128 : 1}
                  max={k === "imgsz" ? 2048 : k === "epochs" ? 1000 : 128}
                  step={k === "imgsz" ? 32 : 1}
                  value={form[k]}
                  onChange={(e) =>
                    setForm({ ...form, [k]: Number(e.target.value) })
                  }
                  required
                />
              ))}
              <Select
                label="Fine-tune existing model (optional)"
                value={form.source_id}
                onChange={(value) => setForm({ ...form, source_id: value })}
                options={[
                  { value: "", label: "Train from base weights" },
                  ...models
                    .filter((m) => m.pt_path)
                    .map((m) => ({ value: Number(m.id), label: text(m.name) })),
                ]}
              />
            </div>
            {form.source_id && (
              <>
                <Input
                  label="Learning rate"
                  type="number"
                  min={0.000001}
                  max={0.1}
                  step="any"
                  value={form.learning_rate}
                  onChange={(e) =>
                    setForm({ ...form, learning_rate: Number(e.target.value) })
                  }
                />
                <Check
                  label="Add new dataset classes to the source model"
                  checked={form.extend_classes}
                  onChange={(e) =>
                    setForm({ ...form, extend_classes: e.target.checked })
                  }
                />
                <Check
                  label="Freeze backbone"
                  checked={form.freeze_backbone}
                  onChange={(e) =>
                    setForm({ ...form, freeze_backbone: e.target.checked })
                  }
                />
                <p className={styles.muted}>
                  Classes are matched by name. Include examples of the old
                  classes to help preserve what the model has learned.
                </p>
              </>
            )}
            <Button variant="primary" type="submit" busy={busy}>
              Start training
            </Button>
          </>
        )}
      </form>
    </Panel>
  );
}
