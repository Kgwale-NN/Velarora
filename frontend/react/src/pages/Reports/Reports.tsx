import { useState } from "react";
import { FileDown, Eye, ArrowLeft } from "lucide-react";
import { useResource, text, type Row } from "../../lib/useResource";
import { download, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { RecordTable } from "../../components/RecordTable/RecordTable";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import { Snapshot } from "../../components/Snapshot/Snapshot";
import styles from "./Reports.module.css";
export function Reports({ notify }: { notify: Notify }) {
  const r = useResource<Row[]>("/teacher/reports");
  const [selected, setSelected] = useState<number | null>(null),
    [shot, setShot] = useState<number | null>(null);
  return (
    <div className={styles.page}>
      <h1>Exam reports</h1>
      {selected !== null ? (
        <Details
          id={selected}
          back={() => setSelected(null)}
          notify={notify}
          showShot={setShot}
        />
      ) : (
        <>
          <ResourceState {...r} retry={r.reload} />
          {r.data && (
            <RecordTable
              rows={r.data}
              columns={[
                { key: "id", label: "Exam" },
                { key: "group_name", label: "Classroom" },
                { key: "started_at", label: "Started" },
                { key: "ended_at", label: "Ended" },
                { key: "total_events", label: "Captures" },
                { key: "alert_count", label: "Alerts" },
                {
                  key: "view",
                  label: "Report",
                  render: (row) => (
                    <Button onClick={() => setSelected(Number(row.id))}>
                      <Eye size={17} />
                      View
                    </Button>
                  ),
                },
              ]}
            />
          )}
        </>
      )}
      {shot !== null && <Snapshot id={shot} onClose={() => setShot(null)} />}
    </div>
  );
}
function Details({
  id,
  back,
  notify,
  showShot,
}: {
  id: number;
  back: () => void;
  notify: Notify;
  showShot: (id: number) => void;
}) {
  const r = useResource<{
    run: Row;
    alerts: Row[];
    classes: Row[];
    students: Row[];
    computers: Row[];
    applications: Row[];
  }>(`/teacher/reports/${id}`);
  async function save(kind: string) {
    try {
      await download(`/teacher/reports/${id}/${kind}`, `exam-${id}.${kind}`);
    } catch (e) {
      notify(errorText(e), "error");
    }
  }
  return (
    <>
      <div className={styles.actions}>
        <Button onClick={back}>
          <ArrowLeft size={17} />
          All reports
        </Button>
        <Button onClick={() => save("pdf")}>
          <FileDown size={17} />
          Download PDF
        </Button>
        <Button onClick={() => save("csv")}>Download CSV</Button>
      </div>
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <>
          <Panel title={"Exam " + id}>
            <p>
              {text(r.data.run.started_at)} — {text(r.data.run.ended_at)}
            </p>
            <p>
              {text(r.data.run.model_name)} · {text(r.data.run.status)}
            </p>
          </Panel>
          {(["applications", "classes", "students", "computers"] as const).map(
            (key) => (
              <Panel
                key={key}
                title={key.charAt(0).toUpperCase() + key.slice(1)}
              >
                <RecordTable
                  rows={r.data![key]}
                  columns={Object.keys(r.data![key][0] || {})
                    .slice(0, 6)
                    .map((k) => ({ key: k, label: k.replaceAll("_", " ") }))}
                />
              </Panel>
            ),
          )}
          <Panel title="Alerts">
            <RecordTable
              rows={r.data.alerts}
              columns={[
                { key: "detected_at", label: "Time" },
                { key: "computer", label: "Computer" },
                { key: "class_name", label: "Detection" },
                {
                  key: "event_id",
                  label: "Screenshot",
                  render: (a) => (
                    <Button onClick={() => showShot(Number(a.event_id))}>
                      View screen
                    </Button>
                  ),
                },
              ]}
            />
          </Panel>
        </>
      )}
    </>
  );
}
