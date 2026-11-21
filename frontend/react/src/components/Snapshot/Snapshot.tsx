import { useState } from "react";
import { useResource } from "../../lib/useResource";
import { Modal } from "../Modal/Modal";
import { Check } from "../Check/Check";
import { ResourceState } from "../ResourceState/ResourceState";
import styles from "./Snapshot.module.css";
export function Snapshot({ id, onClose }: { id: number; onClose: () => void }) {
  const r = useResource<{ raw: string | null; annotated: string | null }>(
    `/teacher/snapshots/${id}`,
  );
  const [annotations, setAnnotations] = useState(true);
  const source = annotations ? r.data?.annotated : r.data?.raw;
  return (
    <Modal title="Screen capture" onClose={onClose}>
      <ResourceState {...r} retry={r.reload} />
      <Check
        label="Show detections"
        checked={annotations}
        onChange={(e) => setAnnotations(e.target.checked)}
      />
      {source ? (
        <img
          className={styles.image}
          src={
            source.startsWith("data:")
              ? source
              : "data:image/jpeg;base64," + source
          }
          alt="Captured student screen"
        />
      ) : (
        !r.loading && <p>No screenshot is available for this event.</p>
      )}
    </Modal>
  );
}
