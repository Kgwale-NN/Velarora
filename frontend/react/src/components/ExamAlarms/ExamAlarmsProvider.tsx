import { createContext, useContext, useState, type ReactNode } from "react";
import { useResource, type Row } from "../../lib/useResource";
import { api, json, errorText } from "../../lib/api";
import type { Notify } from "../../lib/types";
type Alarms = {
  rows: Row[];
  loading: boolean;
  error: string;
  busy: number | null;
  reload: () => void;
  stop: (id: number) => Promise<void>;
};
const Context = createContext<Alarms | null>(null);
export function ExamAlarmsProvider({
  enabled,
  notify,
  children,
}: {
  enabled: boolean;
  notify: Notify;
  children: ReactNode;
}) {
  const resource = useResource<Row[]>(enabled ? "/teacher/alarms" : null, 3000);
  const [busy, setBusy] = useState<number | null>(null);
  async function stop(id: number) {
    if (busy !== null) return;
    setBusy(id);
    try {
      await api(`/teacher/alarms/${id}/stop`, json("POST"));
      resource.reload();
      notify("Alarm stop requested.");
    } catch (error) {
      notify(errorText(error), "error");
    } finally {
      setBusy(null);
    }
  }
  return (
    <Context.Provider
      value={{
        rows: resource.data || [],
        loading: resource.loading,
        error: resource.error,
        busy,
        reload: resource.reload,
        stop,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useExamAlarms() {
  const value = useContext(Context);
  if (!value) throw new Error("Exam alarms require a provider.");
  return value;
}
