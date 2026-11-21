import { PageSkeleton } from "../../components/PageSkeleton/PageSkeleton";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import { useState } from "react";
import { useResource, text, type Row } from "../../lib/useResource";
import { api, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { Check } from "../../components/Check/Check";
import { Panel } from "../../components/Panel/Panel";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./ModelRules.module.css";
export function ModelRules({ notify }: { notify: Notify }) {
  const r = useResource<{ model: Row | null; rules: Row[] }>(
    "/admin/model-alert-rules",
  );
  const [busy, setBusy] = useState<number | null>(null);
  const names = r.data?.model?.class_names as string[] | undefined;
  if (r.loading && !r.data) return <PageSkeleton />;
  return (
    <div className={styles.page}>
      <PageHeading
        title="Model alert rules"
        description="Choose detected classes that raise an alert. Allowed classes still appear in history. Exam schedules can override these defaults."
      />
      <ResourceState {...r} retry={r.reload} />
      <Panel
        title={r.data?.model ? text(r.data.model.name) : "Detection classes"}
      >
        {r.data?.rules
          .filter((c) => !names || names.includes(text(c.name)))
          .map((c) => (
            <Check
              key={Number(c.class_id)}
              label={
                text(c.name) + " — " + (c.enabled ? "Prohibited" : "Allowed")
              }
              checked={!!c.enabled}
              disabled={busy !== null}
              onChange={async (e) => {
                setBusy(Number(c.class_id));
                try {
                  await api(
                    "/admin/model-alert-rules/" + c.class_id,
                    json("PUT", { enabled: e.target.checked }),
                  );
                  r.reload();
                  notify("Alert rule updated.");
                } catch (e) {
                  notify(errorText(e), "error");
                } finally {
                  setBusy(null);
                }
              }}
            />
          ))}
      </Panel>
    </div>
  );
}
