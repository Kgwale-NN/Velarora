import { useState } from "react";
import { useResource, type Row } from "../../lib/useResource";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import { Panel } from "../../components/Panel/Panel";
import { RecordTable } from "../../components/RecordTable/RecordTable";
import { ResourceState } from "../../components/ResourceState/ResourceState";
import styles from "./Audit.module.css";
export function Audit() {
  const [limit, setLimit] = useState("200"),
    [action, setAction] = useState(""),
    [query, setQuery] = useState("limit=200");
  const r = useResource<Row[]>("/admin/audit?" + query);
  return (
    <div className={styles.page}>
      <h1>Audit log</h1>
      <p className={styles.muted}>
        A record of account, model, classroom and system changes.
      </p>
      <Panel>
        <form
          className={styles.toolbar}
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(
              new URLSearchParams({
                limit,
                ...(action && { action }),
              }).toString(),
            );
            r.reload();
          }}
        >
          <Input
            label="Maximum rows"
            type="number"
            min={1}
            max={1000}
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            required
          />
          <Input
            label="Action"
            placeholder="Filter by action"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          />
          <Button type="submit">Apply filter</Button>
        </form>
      </Panel>
      <ResourceState {...r} retry={r.reload} />
      {r.data && (
        <RecordTable
          rows={r.data}
          columns={[
            { key: "created_at", label: "Time" },
            { key: "username", label: "User" },
            { key: "action", label: "Action" },
            { key: "entity", label: "Entity" },
            { key: "entity_id", label: "Record" },
            { key: "detail", label: "Details" },
          ]}
        />
      )}
    </div>
  );
}
