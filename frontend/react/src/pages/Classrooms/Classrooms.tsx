import { useEffect, useState, type FormEvent } from "react";
import {
  School,
  Monitor,
  Plus,
  Search,
  RefreshCw,
  Pencil,
  Trash2,
  Download,
  Check,
  ArrowUpRight,
} from "lucide-react";
import { adminApi as api, errorText } from "../../lib/api";
import type { Classroom, Computer, Notify } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import { Input } from "../../components/Input/Input";
import { Modal } from "../../components/Modal/Modal";
import { StatCard } from "../../components/StatCard/StatCard";
import { DataTable } from "../../components/DataTable/DataTable";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import styles from "./Classrooms.module.css";
export function Classrooms({ notify }: { notify: Notify }) {
  const [rooms, setRooms] = useState<Classroom[]>([]),
    [computers, setComputers] = useState<Computer[]>([]),
    [loading, setLoading] = useState(true),
    [failure, setFailure] = useState(""),
    [query, setQuery] = useState(""),
    [editing, setEditing] = useState<Classroom | null | undefined>(undefined),
    [deleting, setDeleting] = useState<Classroom | null>(null),
    [assigning, setAssigning] = useState<Classroom | null>(null),
    [selected, setSelected] = useState<number[]>([]),
    [membersLoading, setMembersLoading] = useState(false),
    [membersReady, setMembersReady] = useState(false),
    [pcSearch, setPcSearch] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function load() {
    setLoading(true);
    setFailure("");
    try {
      const data = await api<{
        classrooms: Classroom[];
        computers: Computer[];
      }>("/classrooms");
      setRooms(data.classrooms);
      setComputers(data.computers);
    } catch (err) {
      setFailure(errorText(err));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api("/classrooms" + (editing ? "/" + editing.id : ""), {
        method: editing ? "PUT" : "POST",
        body: JSON.stringify(Object.fromEntries(form)),
      });
      setEditing(undefined);
      notify(
        editing
          ? "Classroom updated."
          : "Classroom created. Now assign its PCs.",
      );
      await load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  async function assign(room: Classroom) {
    setAssigning(room);
    setPcSearch("");
    setSelected([]);
    setError("");
    setMembersLoading(true);
    setMembersReady(false);
    try {
      setSelected(await api<number[]>("/classrooms/" + room.id + "/members"));
      setMembersReady(true);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setMembersLoading(false);
    }
  }
  async function saveMembers() {
    if (!assigning) return;
    setBusy(true);
    setError("");
    try {
      await api("/classrooms/" + assigning.id + "/members", {
        method: "PUT",
        body: JSON.stringify({ computer_ids: selected }),
      });
      setAssigning(null);
      notify("Classroom computers updated.");
      await load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    if (!deleting) return;
    setBusy(true);
    setError("");
    try {
      await api("/classrooms/" + deleting.id, { method: "DELETE" });
      setDeleting(null);
      notify("Classroom removed. Registered PCs are retained.");
      await load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  async function importRooms() {
    setBusy(true);
    try {
      const result = await api<{ classrooms: number; computers: number }>(
        "/classrooms/import",
        { method: "POST", body: "{}" },
      );
      notify(
        result.classrooms
          ? `Imported ${result.classrooms} classrooms and ${result.computers} computers.`
          : "No Veyon locations were found.",
      );
      await load();
    } catch (err) {
      notify(errorText(err), "error");
    } finally {
      setBusy(false);
    }
  }
  const shown = rooms.filter((r) =>
    `${r.name} ${r.description || ""}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  return (
    <section className={styles.page}>
      <PageHeading
        eyebrow="Spaces & connections"
        title="Classroom setup"
        description="Give every exam a home. Organise your rooms, connect their PCs, and prepare the big screens."
        action={
          <Button
            variant="primary"
            onClick={() => {
              setEditing(null);
              setError("");
            }}
          >
            <Plus size={18} />
            New classroom
          </Button>
        }
      />
      <div className={styles.stats}>
        <StatCard
          label="Classrooms"
          value={loading ? "—" : rooms.length}
          icon={<School />}
          note="Available to any teacher"
        />
        <StatCard
          label="Registered computers"
          value={loading ? "—" : computers.length}
          icon={<Monitor />}
          note="Imported from your Veyon setup"
        />
        <StatCard
          label="Rooms with PCs"
          value={
            loading ? "—" : rooms.filter((r) => r.computer_count > 0).length
          }
          icon={<Check />}
          note="Ready for classroom selection"
        />
      </div>
      <div className={styles.guide}>
        <span>
          01 <strong>Create a classroom</strong>
        </span>
        <i />
        <span>
          02 <strong>Assign its PCs</strong>
        </span>
        <i />
        <span>
          03 <strong>Open the big screen</strong>
        </span>
      </div>
      <div className={styles.toolbar}>
        <div className={styles.search}>
          <Input
            label="Find a classroom"
            placeholder="Search a room or description…"
            icon={<Search />}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <Button onClick={importRooms} busy={busy}>
          <Download size={17} />
          Import from Veyon
        </Button>
        <Button
          aria-label="Refresh classrooms"
          variant="ghost"
          onClick={() => void load()}
          busy={loading}
        >
          <RefreshCw size={17} />
        </Button>
      </div>
      {failure && (
        <p role="alert" className={styles.error}>
          {failure}
          <Button onClick={() => void load()}>Try again</Button>
        </p>
      )}
      <DataTable
        busy={loading}
        rows={shown}
        empty="Your first classroom starts here"
        columns={[
          {
            key: "name",
            label: "Classroom",
            render: (r) => (
              <div className={styles.identity}>
                <span className={styles.roomIcon}>
                  <School size={19} />
                </span>
                <span>
                  {r.name}
                  <small>{r.description || "No description added"}</small>
                </span>
              </div>
            ),
          },
          {
            key: "computers",
            label: "Computers",
            render: (r) => (
              <span className={styles.count}>
                {r.computer_count}{" "}
                <span>PC{r.computer_count === 1 ? "" : "s"}</span>
              </span>
            ),
          },
          {
            key: "status",
            label: "Setup",
            render: (r) => (
              <span className={styles.badge}>
                {r.computer_count ? "PCs assigned" : "Needs computers"}
              </span>
            ),
          },
          {
            key: "screen",
            label: "Big screen",
            render: (r) => (
              <a className={styles.link} href={"/?classroom=" + r.id}>
                Open classroom
                <ArrowUpRight size={14} />
              </a>
            ),
          },
          {
            key: "actions",
            label: "Manage",
            render: (r) => (
              <div className={styles.actions}>
                <Button
                  variant="ghost"
                  aria-label={"Assign computers to " + r.name}
                  onClick={() => void assign(r)}
                >
                  <Monitor size={17} />
                </Button>
                <Button
                  variant="ghost"
                  aria-label={"Edit " + r.name}
                  onClick={() => {
                    setEditing(r);
                    setError("");
                  }}
                >
                  <Pencil size={16} />
                </Button>
                <Button
                  variant="ghost"
                  aria-label={"Delete " + r.name}
                  onClick={() => {
                    setDeleting(r);
                    setError("");
                  }}
                >
                  <Trash2 size={16} />
                </Button>
              </div>
            ),
          },
        ]}
      />
      <p className={styles.note}>
        Classrooms organise existing PCs. Screen capture still needs a working
        Veyon connection; workstation alarms need the agent.
      </p>
      {editing !== undefined && (
        <Modal
          title={editing ? "Edit classroom" : "Create classroom"}
          onClose={() => setEditing(undefined)}
          busy={busy}
        >
          <form onSubmit={save}>
            <Input
              label="Classroom name"
              name="name"
              required
              maxLength={100}
              placeholder="e.g. Lab 1"
              defaultValue={editing?.name || ""}
              icon={<School />}
            />
            <Input
              label="Description"
              name="description"
              maxLength={500}
              placeholder="e.g. Ground floor computer lab"
              defaultValue={editing?.description || ""}
            />
            {error && <p role="alert">{error}</p>}
            <footer>
              <Button
                type="button"
                onClick={() => setEditing(undefined)}
                disabled={busy}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" busy={busy}>
                Save classroom
              </Button>
            </footer>
          </form>
        </Modal>
      )}
      {assigning && (
        <Modal
          title={"PCs in " + assigning.name}
          onClose={() => setAssigning(null)}
          busy={busy || membersLoading}
        >
          <Input
            label="Find a computer"
            placeholder="Search registered PCs…"
            icon={<Search />}
            value={pcSearch}
            onChange={(e) => setPcSearch(e.target.value)}
          />
          <p>
            {selected.length} computer{selected.length === 1 ? "" : "s"}{" "}
            selected
          </p>
          <div className={styles.choices}>
            {membersLoading ? (
              <p>Loading computers…</p>
            ) : (
              computers
                .filter((c) =>
                  c.name.toLowerCase().includes(pcSearch.toLowerCase()),
                )
                .map((c) => (
                  <label key={c.id}>
                    <input
                      type="checkbox"
                      checked={selected.includes(c.id)}
                      disabled={busy}
                      onChange={(e) =>
                        setSelected((ids) =>
                          e.target.checked
                            ? [...ids, c.id]
                            : ids.filter((id) => id !== c.id),
                        )
                      }
                    />
                    <Monitor size={17} />
                    <span>
                      {c.name}
                      <small>{c.host_address}</small>
                    </span>
                  </label>
                ))
            )}
            {!membersLoading && !computers.length && (
              <p>No registered PCs yet. Import your Veyon locations first.</p>
            )}
          </div>
          {error && <p role="alert">{error}</p>}
          <footer>
            <Button
              disabled={busy || membersLoading}
              onClick={() => setAssigning(null)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              busy={busy}
              disabled={membersLoading || !membersReady}
              onClick={saveMembers}
            >
              Save computers
            </Button>
          </footer>
        </Modal>
      )}
      {deleting && (
        <Modal
          title="Delete this classroom?"
          onClose={() => setDeleting(null)}
          busy={busy}
        >
          <p>
            Remove <strong>{deleting.name}</strong> and its linked schedules?
            Registered computers and saved exam records remain. End any running
            exam first.
          </p>
          {error && <p role="alert">{error}</p>}
          <footer>
            <Button disabled={busy} onClick={() => setDeleting(null)}>
              Keep classroom
            </Button>
            <Button variant="danger" busy={busy} onClick={remove}>
              Delete classroom
            </Button>
          </footer>
        </Modal>
      )}
    </section>
  );
}
