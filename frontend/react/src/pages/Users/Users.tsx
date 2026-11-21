import { PageSkeleton } from "../../components/PageSkeleton/PageSkeleton";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  UsersRound,
  UserCheck,
  GraduationCap,
  UserRound,
  Plus,
  Search,
  Trash2,
  Mail,
  LockKeyhole,
} from "lucide-react";
import { adminApi as api, errorText } from "../../lib/api";
import type { User, Notify } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import { Input } from "../../components/Input/Input";
import { Modal } from "../../components/Modal/Modal";
import { StatCard } from "../../components/StatCard/StatCard";
import { DataTable } from "../../components/DataTable/DataTable";
import { PageHeading } from "../../components/PageHeading/PageHeading";
import styles from "./Users.module.css";
export function Users({
  notify,
  currentId,
}: {
  notify: Notify;
  currentId: number;
}) {
  const initialized = useRef(false);
  const [users, setUsers] = useState<User[]>([]),
    [loading, setLoading] = useState(true),
    [failure, setFailure] = useState(""),
    [query, setQuery] = useState(""),
    [role, setRole] = useState("all"),
    [create, setCreate] = useState(false),
    [reset, setReset] = useState<User | null>(null),
    [deleting, setDeleting] = useState<User | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function load() {
    setLoading(true);
    setFailure("");
    try {
      setUsers(await api<User[]>("/users"));
    } catch (err) {
      setFailure(errorText(err));
    } finally {
      initialized.current = true;
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api("/users", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(data)),
      });
      setCreate(false);
      notify("Teacher account created.");
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
      await api("/users/" + deleting.id, { method: "DELETE" });
      setDeleting(null);
      notify("User removed. Exam records were retained.");
      await load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  const staff = users.filter((u) => u.role !== "student");
  const shown = users.filter(
    (u) =>
      (role === "all" || u.role === role) &&
      `${u.username} ${u.email || ""}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  if (loading && !initialized.current) return <PageSkeleton />;
  return (
    <section className={styles.page}>
      <PageHeading
        eyebrow="People & access"
        title="User dashboard"
        description="A clear view of your people. Manage teacher access and keep student records together."
        action={
          <Button
            variant="primary"
            onClick={() => {
              setCreate(true);
              setError("");
            }}
          >
            <Plus size={18} />
            Add user
          </Button>
        }
      />
      <div className={styles.stats}>
        <StatCard
          label="Total users"
          value={loading ? "—" : users.length}
          icon={<UsersRound />}
          note="Across your workspace"
        />
        <StatCard
          label="Active accounts"
          value={loading ? "—" : staff.filter((u) => u.is_active).length}
          icon={<UserCheck />}
          note="Staff with sign-in access"
        />
        <StatCard
          label="Teachers"
          value={
            loading ? "—" : users.filter((u) => u.role === "teacher").length
          }
          icon={<GraduationCap />}
          note="Ready to lead an exam"
        />
        <StatCard
          label="Student records"
          value={
            loading ? "—" : users.filter((u) => u.role === "student").length
          }
          icon={<UserRound />}
          note="Recorded automatically · no login"
        />
      </div>
      <div className={styles.sectionTitle}>
        <h2>Everyone in your workspace</h2>
        <span>{shown.length} records</span>
      </div>
      <div className={styles.toolbar}>
        <div className={styles.search}>
          <Input
            label="Search users"
            placeholder="Search a name or email…"
            icon={<Search />}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className={styles.filters} aria-label="Filter by role">
          {[
            ["all", "Everyone"],
            ["teacher", "Teachers"],
            ["student", "Students"],
          ].map(([value, label]) => (
            <button
              key={value}
              className={role === value ? styles.selected : ""}
              aria-pressed={role === value}
              onClick={() => setRole(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {failure && (
        <p className={styles.error} role="alert">
          {failure} <Button onClick={() => void load()}>Try again</Button>
        </p>
      )}
      <DataTable
        busy={loading}
        rows={shown}
        columns={[
          {
            key: "name",
            label: "User",
            render: (u) => (
              <div className={styles.identity}>
                <span className={styles.avatar}>
                  {u.username.charAt(0).toUpperCase()}
                </span>
                <span>
                  {u.username}
                  {u.id === currentId && <small>You</small>}
                </span>
              </div>
            ),
          },
          {
            key: "email",
            label: "Email address",
            render: (u) => (
              <span className={styles.muted}>
                {u.email || "No sign-in email"}
              </span>
            ),
          },
          {
            key: "role",
            label: "Role",
            render: (u) => (
              <span className={styles.badge}>
                {u.role === "admin"
                  ? "Administrator"
                  : u.role === "teacher"
                    ? "Teacher"
                    : "Student"}
              </span>
            ),
          },
          {
            key: "status",
            label: "Access",
            render: (u) => (
              <span
                className={styles.status}
                data-active={u.role !== "student" && !!u.is_active}
              >
                {u.role === "student"
                  ? "No web access"
                  : u.is_active
                    ? "Active"
                    : "Inactive"}
              </span>
            ),
          },
          {
            key: "date",
            label: "Created",
            render: (u) => (
              <span className={styles.muted}>{u.created_at.split(" ")[0]}</span>
            ),
          },
          {
            key: "actions",
            label: "Manage",
            render: (u) =>
              u.role !== "admin" && (
                <div>
                  {u.role === "teacher" && (
                    <Button
                      variant="ghost"
                      aria-label={"Reset password for " + u.username}
                      onClick={() => {
                        setReset(u);
                        setError("");
                      }}
                    >
                      <LockKeyhole size={17} />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    aria-label={"Delete " + u.username}
                    onClick={() => {
                      setDeleting(u);
                      setError("");
                    }}
                  >
                    <Trash2 size={17} />
                  </Button>
                </div>
              ),
          },
        ]}
      />
      <p className={styles.note}>
        <LockKeyhole size={14} />
        Only administrators can manage accounts. Student records never provide
        website access.
      </p>
      {reset && (
        <Modal
          title="Reset teacher password"
          onClose={() => setReset(null)}
          busy={busy}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const data = new FormData(e.currentTarget);
              setBusy(true);
              setError("");
              try {
                await api("/users/" + reset.id + "/password", {
                  method: "PUT",
                  body: JSON.stringify({ password: data.get("password") }),
                });
                notify("Password reset. Share it with the teacher privately.");
                setReset(null);
              } catch (e) {
                setError(errorText(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            <p>{reset.username}</p>
            <Input
              label="New temporary password"
              placeholder="New temporary password"
              name="password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              required
              hint="At least 12 characters. Start with a capital letter and include a number and symbol."
            />
            {error && <p role="alert">{error}</p>}
            <footer>
              <Button
                type="button"
                onClick={() => setReset(null)}
                disabled={busy}
              >
                Cancel
              </Button>
              <Button type="submit" busy={busy}>
                Reset password
              </Button>
            </footer>
          </form>
        </Modal>
      )}
      {create && (
        <Modal
          title="Create teacher account"
          onClose={() => setCreate(false)}
          busy={busy}
        >
          <form onSubmit={add}>
            <Input
              label="Display name"
              name="username"
              placeholder="Enter the teacher’s name"
              required
              maxLength={100}
              icon={<UserRound />}
            />
            <Input
              label="Email address"
              name="email"
              type="email"
              placeholder="teacher@school.com"
              required
              icon={<Mail />}
            />
            <Input
              label="Temporary password"
              name="password"
              type="password"
              placeholder="Create a strong password"
              required
              minLength={12}
              autoComplete="new-password"
              icon={<LockKeyhole />}
              hint="At least 12 characters. Start with a capital letter; include a number and a symbol."
            />
            <p>
              This creates a teacher account. Students are added automatically
              during monitoring.
            </p>
            {error && <p role="alert">{error}</p>}
            <footer>
              <Button
                type="button"
                disabled={busy}
                onClick={() => setCreate(false)}
              >
                Cancel
              </Button>
              <Button variant="primary" type="submit" busy={busy}>
                Create account
              </Button>
            </footer>
          </form>
        </Modal>
      )}
      {deleting && (
        <Modal
          title="Delete this user?"
          onClose={() => setDeleting(null)}
          busy={busy}
        >
          <p>
            Remove <strong>{deleting.username}</strong>? Their saved exam
            records will remain. Running exams and alarms must be finished
            first.
          </p>
          {error && <p role="alert">{error}</p>}
          <footer>
            <Button disabled={busy} onClick={() => setDeleting(null)}>
              Keep user
            </Button>
            <Button variant="danger" busy={busy} onClick={remove}>
              Delete user
            </Button>
          </footer>
        </Modal>
      )}
    </section>
  );
}
