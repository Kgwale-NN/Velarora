import { PageSkeleton } from "../../components/PageSkeleton/PageSkeleton";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import { useState } from "react";
import { Activity, Users, ScanEye } from "lucide-react";
import { useResource, text, type Row } from "../../lib/useResource";
import { Input } from "../../components/Input/Input";
import { Select } from "../../components/Select/Select";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { StatCard } from "../../components/StatCard/StatCard";
import { Bars } from "../../components/Bars/Bars";
import { RecordTable } from "../../components/RecordTable/RecordTable";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./Analytics.module.css";
export function Analytics() {
  const [start, setStart] = useState(""),
    [end, setEnd] = useState(""),
    [computer, setComputer] = useState(""),
    [student, setStudent] = useState(""),
    [query, setQuery] = useState("");
  const choices = useResource<{ computers: Row[]; students: Row[] }>(
    "/teacher/options",
  );
  const r = useResource<{
    summary: Row;
    classes: Row[];
    daily: Row[];
    students: Row[];
  }>("/teacher/analytics?" + query);
  const opts = (rows: Row[], key: string) => [
    { value: "", label: "All" },
    ...rows.map((v) => ({ value: Number(v.id), label: text(v[key]) })),
  ];
  if (r.loading && !r.data) return <PageSkeleton />;
  return (
    <div className={styles.page}>
      <PageHeading
        title="Your analytics"
        description="Review captures and detections across your exams."
      />
      <Panel>
        <form
          className={styles.toolbar}
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(
              new URLSearchParams({
                start,
                end,
                ...(computer && { computer_id: computer }),
                ...(student && { user_id: student }),
              }).toString(),
            );
            r.reload();
          }}
        >
          <Input
            label="From date"
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
          <Input
            label="To date"
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
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
          <Button type="submit">Apply filters</Button>
        </form>
      </Panel>
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <>
          <div className={styles.stats}>
            <StatCard
              label="Screen captures"
              value={Number(r.data.summary.total_events)}
              icon={<Activity />}
            />
            <StatCard
              label="Detections"
              value={Number(r.data.summary.detection_events)}
              icon={<ScanEye />}
            />
            <StatCard
              label="Active students"
              value={Number(r.data.summary.active_students)}
              icon={<Users />}
            />
          </div>
          <div className={styles.split}>
            <Panel title="Detected applications">
              <Bars
                rows={r.data.classes.map((c) => ({
                  label: text(c.name),
                  value: Number(c.count),
                }))}
              />
            </Panel>
            <Panel title="Daily activity">
              <Bars
                rows={r.data.daily.map((c) => ({
                  label: text(c.date || c.day),
                  value: Number(c.hits || 0),
                }))}
              />
            </Panel>
          </div>
          <Panel title="Student activity">
            <RecordTable
              rows={r.data.students}
              columns={[
                { key: "student", label: "Student" },

                { key: "hits", label: "Detections" },
              ]}
            />
          </Panel>
        </>
      )}
    </div>
  );
}
