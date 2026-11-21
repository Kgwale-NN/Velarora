import { PageSkeleton } from "../../components/PageSkeleton/PageSkeleton";
import { FormActions } from "../../components/FormActions/FormActions";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { useResource, text } from "../../lib/useResource";
import { api, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { Input } from "../../components/Input/Input";
import { Select } from "../../components/Select/Select";
import { Check } from "../../components/Check/Check";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./Settings.module.css";
const sections: [string, [string, string, string?][]][] = [
  [
    "Authentication",
    [
      ["auth_method", "Authentication method", "auth"],
      ["key_name", "Key name"],
      ["key_path", "Key file path (.pem)"],
      ["logon_username", "Logon username"],
      ["logon_password", "Logon password", "password"],
    ],
  ],
  [
    "Veyon connection",
    [
      ["veyon_cli", "Veyon CLI executable"],
      ["host", "Host"],
      ["port", "Port", "number"],
      ["auto_start", "Auto-start server", "check"],
      ["start_wait", "Start-up wait (seconds)", "number"],
    ],
  ],
  [
    "Screen capture",
    [
      ["interval", "Poll interval (seconds)", "number"],
      ["img_fmt", "Image format", "format"],
      ["img_quality", "JPEG quality (1–100)", "number"],
      ["img_width", "Capture width (pixels)", "number"],
    ],
  ],
  [
    "Detection",
    [
      ["detect_conf", "Confidence threshold (0–1)", "number"],
      ["detect_iou", "IoU threshold (0–1)", "number"],
      ["keep_top1", "Keep top detection per class", "check"],
      ["batch_max_cuda", "GPU maximum batch size", "number"],
      ["batch_max_cpu", "CPU maximum batch size", "number"],
      ["detect_cycle_timing", "Log detection cycle timing", "check"],
      ["alert_threshold", "Consecutive detections before alert", "number"],
    ],
  ],
  [
    "Data retention",
    [
      [
        "retention_days",
        "Delete events older than (days; 0 keeps forever)",
        "number",
      ],
    ],
  ],
];
export function Settings({ notify }: { notify: Notify }) {
  const r =
    useResource<Record<string, string | number | boolean>>("/admin/settings");
  const [form, setForm] = useState<Record<string, string | number | boolean>>(
      {},
    ),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (r.data) setForm(r.data);
  }, [r.data]);
  const update = (key: string, value: string | number | boolean) =>
    setForm({ ...form, [key]: value });
  if (r.loading && !r.data) return <PageSkeleton />;
  return (
    <div className={styles.page}>
      <PageHeading
        title="Settings"
        description="Changes apply the next time monitoring starts. Activate a model on Models to set the model path and inference size."
      />
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <form
          className={styles.form}
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            try {
              await api("/admin/settings", json("PUT", form));
              notify("Settings saved.");
            } catch (e) {
              notify(errorText(e), "error");
            } finally {
              setBusy(false);
            }
          }}
        >
          {sections.map(([title, fields]) => (
            <Panel key={title} title={title}>
              <div className={styles.grid}>
                {fields.map(([key, label, kind]) =>
                  kind === "check" ? (
                    <Check
                      key={key}
                      label={label}
                      checked={!!form[key]}
                      onChange={(e) => update(key, e.target.checked)}
                    />
                  ) : kind === "auth" || kind === "format" ? (
                    <Select
                      key={key}
                      label={label}
                      value={text(form[key])}
                      onChange={(value) => update(key, value)}
                      options={
                        kind === "auth"
                          ? [
                              { value: "key", label: "Cryptographic key" },
                              { value: "logon", label: "Logon credentials" },
                            ]
                          : [
                              { value: "jpeg", label: "JPEG" },
                              { value: "png", label: "PNG" },
                            ]
                      }
                    />
                  ) : (
                    <Input
                      key={key}
                      label={label}
                      type={kind || "text"}
                      step={kind === "number" ? "any" : undefined}
                      placeholder={
                        kind === "password"
                          ? "Leave blank to keep current password"
                          : label
                      }
                      value={text(form[key] ?? "")}
                      onChange={(e) =>
                        update(
                          key,
                          kind === "number"
                            ? Number(e.target.value)
                            : e.target.value,
                        )
                      }
                    />
                  ),
                )}
              </div>
            </Panel>
          ))}
          <FormActions>
            <Button variant="primary" busy={busy} type="submit">
              <Save size={18} />
              Save settings
            </Button>
          </FormActions>
        </form>
      )}
    </div>
  );
}
