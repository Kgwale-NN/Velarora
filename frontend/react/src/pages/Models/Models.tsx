import { PageSkeleton } from "../../components/PageSkeleton/PageSkeleton";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import { useEffect, useState } from "react";
import { Plus, Upload, Play, Pencil, Trash2, RefreshCw } from "lucide-react";
import { useResource, text, type Row } from "../../lib/useResource";
import { api, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { Modal } from "../../components/Modal/Modal";
import { RecordTable } from "../../components/RecordTable/RecordTable";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import { Bars } from "../../components/Bars/Bars";
import { ImportModel } from "./ImportModel/ImportModel";
import { TrainingForm } from "./TrainingForm/TrainingForm";
import styles from "./Models.module.css";
type Training = {
  hardware: Row;
  bases: string[];
  job: {
    running: boolean;
    done: boolean;
    status: string;
    batch: Row;
    epochs: Row[];
    model_id: number | null;
    error: string | null;
  } | null;
};
export function Models({ notify }: { notify: Notify }) {
  const r = useResource<Row[]>("/admin/models"),
    training = useResource<Training>("/admin/training", 5000);
  const [edit, setEdit] = useState<Row | null>(null),
    [remove, setRemove] = useState<Row | null>(null),
    [importing, setImporting] = useState(false),
    [showTrain, setShowTrain] = useState(false),
    [busy, setBusy] = useState(false);
  async function action(path: string, method = "POST", payload: unknown = {}) {
    setBusy(true);
    try {
      await api("/admin/models/" + path, json(method, payload));
      r.reload();
      notify("Model library updated.");
      setEdit(null);
      setRemove(null);
    } catch (e) {
      notify(errorText(e), "error");
    } finally {
      setBusy(false);
    }
  }
  const job = training.data?.job;
  useEffect(() => {
    if (job?.model_id) r.reload();
  }, [job?.model_id, r.reload]);
  if ((r.loading && !r.data) || (training.loading && !training.data))
    return <PageSkeleton />;
  return (
    <div className={styles.page}>
      <PageHeading
        title="Model library"
        description="Manage the AI that recognises applications in screenshots."
        action={
          <div className={styles.actions}>
            <Button variant="primary" onClick={() => setShowTrain((v) => !v)}>
              <Plus size={17} />
              Train new model
            </Button>
            <Button onClick={() => setImporting(true)}>
              <Upload size={17} />
              Import model
            </Button>
          </div>
        }
      />
      <Panel title="Training hardware">
        <p>
          {training.data?.hardware.cuda_ok
            ? "NVIDIA GPU available"
            : "CPU training"}{" "}
          · {text(training.data?.hardware.torch_ver)}
        </p>
        <p>
          {training.data?.hardware.cuda_ok
            ? text(training.data.hardware.gpu_name)
            : "Training uses your processor. It can take longer. Installing CUDA does not add an NVIDIA GPU to your PC."}
        </p>
      </Panel>
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <RecordTable
          rows={r.data}
          columns={[
            { key: "name", label: "Model" },
            { key: "nc", label: "Classes" },
            { key: "base_model", label: "Base" },
            { key: "imgsz", label: "Image size" },
            { key: "map50", label: "mAP50" },
            { key: "status", label: "Status" },
            {
              key: "is_active",
              label: "Active",
              render: (m) => (m.is_active ? "Active" : "—"),
            },
            {
              key: "actions",
              label: "Actions",
              render: (m) => (
                <div className={styles.actions}>
                  <Button
                    aria-label="Activate model"
                    disabled={!!m.is_active || busy}
                    onClick={() => action(m.id + "/activate")}
                  >
                    <Play size={17} />
                  </Button>
                  <Button aria-label="Edit model" onClick={() => setEdit(m)}>
                    <Pencil size={17} />
                  </Button>
                  <Button
                    aria-label="Synchronise classes"
                    disabled={busy}
                    onClick={() => action(m.id + "/sync")}
                  >
                    <RefreshCw size={17} />
                  </Button>
                  <Button
                    aria-label="Delete model"
                    disabled={!!m.is_active}
                    onClick={() => setRemove(m)}
                  >
                    <Trash2 size={17} />
                  </Button>
                </div>
              ),
            },
          ]}
        />
      )}
      {showTrain && (
        <TrainingForm
          models={r.data || []}
          bases={training.data?.bases || []}
          notify={notify}
          onStart={() => {
            training.reload();
            setShowTrain(false);
          }}
        />
      )}
      {job && (
        <Panel title="Training progress">
          <p role="status">{job.error || job.status}</p>
          <label>
            Epoch progress
            <progress
              className={styles.progress}
              value={Number(job.batch.epoch || 0)}
              max={Number(job.batch.total_epochs || 1)}
            />
          </label>
          <p>
            Epoch {text(job.batch.epoch || 0)} of{" "}
            {text(job.batch.total_epochs || 0)}
          </p>
          <label>
            Current epoch batches
            <progress
              className={styles.progress}
              value={Number(job.batch.batch || 0)}
              max={Number(job.batch.total_batches || 1)}
            />
          </label>
          <Bars
            rows={job.epochs.map((e) => ({
              label: "Epoch " + e.epoch + " mAP50",
              value: Number(e.map50),
            }))}
          />
          {job.running && (
            <Button
              variant="danger"
              onClick={async () => {
                try {
                  await api("/admin/training/cancel", json("POST"));
                  notify("Training stop requested.");
                  training.reload();
                } catch (e) {
                  notify(errorText(e), "error");
                }
              }}
            >
              Cancel training
            </Button>
          )}
        </Panel>
      )}
      {importing && (
        <ImportModel
          notify={notify}
          onClose={() => setImporting(false)}
          onSave={() => {
            setImporting(false);
            r.reload();
          }}
        />
      )}
      {edit && (
        <Modal title="Edit model" onClose={() => setEdit(null)} busy={busy}>
          <form
            className={styles.form}
            onSubmit={(e) => {
              e.preventDefault();
              void action(String(edit.id), "PUT", {
                name: edit.name,
                imgsz: Number(edit.imgsz),
              });
            }}
          >
            <Input
              label="Model name"
              placeholder="Model name"
              value={text(edit.name)}
              onChange={(e) => setEdit({ ...edit, name: e.target.value })}
              required
            />
            <Input
              label="Inference image size"
              type="number"
              min={128}
              max={2048}
              step={32}
              value={text(edit.imgsz)}
              onChange={(e) => setEdit({ ...edit, imgsz: e.target.value })}
            />
            <p className={styles.muted}>
              Classes: {((edit.class_names as string[]) || []).join(", ")}
            </p>
            <p className={styles.muted}>ONNX: {text(edit.onnx_path)}</p>
            <Button type="submit" busy={busy}>
              Save model
            </Button>
          </form>
        </Modal>
      )}
      {remove && (
        <Modal
          title="Delete model?"
          onClose={() => setRemove(null)}
          busy={busy}
        >
          <p>
            Remove {text(remove.name)} from the library? Saved reports remain
            available.
          </p>
          <footer>
            <Button onClick={() => setRemove(null)}>Cancel</Button>
            <Button
              variant="danger"
              busy={busy}
              onClick={() => action(String(remove.id), "DELETE")}
            >
              Delete model
            </Button>
          </footer>
        </Modal>
      )}
    </div>
  );
}
