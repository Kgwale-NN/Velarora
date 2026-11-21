import { useEffect, useState, useCallback } from "react";
import { api, errorText } from "./api";
export function useResource<T>(path: string, interval = 0) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision((v) => v + 1), []);
  useEffect(() => {
    let active = true,
      busy = false;
    const controller = new AbortController();
    setLoading(true);
    setData(null);
    const load = async () => {
      if (busy) return;
      busy = true;
      try {
        const value = await api<T>(path, { signal: controller.signal });
        if (active) {
          setData(value);
          setError("");
        }
      } catch (e) {
        if (active) setError(errorText(e));
      } finally {
        busy = false;
        if (active) setLoading(false);
      }
    };
    void load();
    const refreshVisible = () => {
      if (!document.hidden) void load();
    };
    const timer = interval ? setInterval(refreshVisible, interval) : undefined;
    document.addEventListener("visibilitychange", refreshVisible);
    return () => {
      active = false;
      controller.abort();
      clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshVisible);
    };
  }, [path, revision, interval]);
  return { data, error, loading, reload, setData };
}
export type Row = Record<string, unknown>;
export function text(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
