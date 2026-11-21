import { PageHeading } from "../../components/PageHeading/PageHeading";
import { useState } from "react";
import { Image, Search } from "lucide-react";
import { useResource, type Row, text } from "../../lib/useResource";
import { Button } from "../../components/Button/Button";
import { Select } from "../../components/Select/Select";
import { Check } from "../../components/Check/Check";
import { Panel } from "../../components/Panel/Panel";
import { RecordTable } from "../../components/RecordTable/RecordTable";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import { Snapshot } from "../../components/Snapshot/Snapshot";
import styles from "./History.module.css";
export function History() {
  const choices = useResource<{
    computers: Row[];
    students: Row[];
    classes: Row[];
  }>("/teacher/options");
  const [computer, setComputer] = useState(""),
    [student, setStudent] = useState(""),
    [klass, setKlass] = useState(""),
    [hits, setHits] = useState(false),
    [offset, setOffset] = useState(0),
    [query, setQuery] = useState(""),
    [shot, setShot] = useState<number | null>(null);
  const r = useResource<{ rows: Row[]; total: number }>(
    `/teacher/history?limit=50&offset=${offset}${query}`,
  );
  const opts = (rows: Row[], key: string) => [
    { value: "", label: "All" },
    ...rows.map((v) => ({ value: Number(v.id), label: text(v[key]) })),
  ];
  return (
    <div className={styles.page}>
      <PageHeading
        title="Detection history"
        description="Your exam activity and saved screenshots."
      />
      <Panel>
        <form
          className={styles.toolbar}
          onSubmit={(e) => {
            e.preventDefault();
            setOffset(0);
            setQuery(
              "&" +
                new URLSearchParams({
                  ...(computer && { computer_id: computer }),
                  ...(student && { user_id: student }),
                  ...(klass && { class_name: klass }),
                  only_hits: String(hits),
                }),
            );
            r.reload();
          }}
        >
          <Select
            label="Computer"
            value={computer}
            onChange={(value) => setComputer(value)}
            options={opts(choices.data?.computers || [], "name")}
          />
          <Select
            label="Student"
            value={student}
            onChange={(value) => setStudent(value)}
            options={opts(choices.data?.students || [], "username")}
          />
          <Select
            label="Detected class"
            value={klass}
            onChange={(value) => setKlass(value)}
            options={[
              { value: "", label: "All" },
              ...(choices.data?.classes || []).map((c) => ({
                value: text(c.name),
                label: text(c.name),
              })),
            ]}
          />
          <Check
            label="Detections only"
            checked={hits}
            onChange={(e) => setHits(e.target.checked)}
          />
          <Button type="submit">
            <Search size={17} />
            Search
          </Button>
        </form>
      </Panel>
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <>
          <RecordTable
            rows={r.data.rows}
            columns={[
              { key: "detected_at", label: "Time" },
              { key: "computer", label: "Computer" },
              { key: "student", label: "Student" },
              { key: "model_name", label: "Model" },
              { key: "foreground_app", label: "Windows app" },
              { key: "detections", label: "Detections" },
              {
                key: "has_frame",
                label: "Screenshot",
                render: (row) => (
                  <Button
                    variant="ghost"
                    disabled={!row.has_frame}
                    aria-label="View screenshot"
                    onClick={() => setShot(Number(row.event_id))}
                  >
                    <Image size={19} />
                  </Button>
                ),
              },
            ]}
          />
          <div className={styles.actions}>
            <Button
              disabled={offset === 0}
              onClick={() => setOffset((v) => Math.max(0, v - 50))}
            >
              Previous
            </Button>
            <span>
              {r.data.total ? offset + 1 : 0}–
              {Math.min(offset + 50, r.data.total)} of {r.data.total}
            </span>
            <Button
              disabled={offset + 50 >= r.data.total}
              onClick={() => setOffset((v) => v + 50)}
            >
              Next
            </Button>
          </div>
        </>
      )}
      {shot !== null && <Snapshot id={shot} onClose={() => setShot(null)} />}
    </div>
  );
}
