import { useEffect, useState, useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";
import { api, errorText } from "./api";
export function useResource<T>(
  path: string | null,
  interval = 0,
  scopeKey?: string | number | null,
) {
  const resourceKey = `${path ?? ""}\u0000${scopeKey ?? ""}`;
  const [resource, setResource] = useState<{ key: string; data: T | null }>(
      () => ({ key: resourceKey, data: null }),
    ),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [revision, setRevision] = useState(0);
  const data = resource.key === resourceKey ? resource.data : null;
  const setData = useCallback<Dispatch<SetStateAction<T | null>>>(
    (next) =>
      setResource((current) => {
        const currentData = current.key === resourceKey ? current.data : null;
        return {
          key: resourceKey,
          data: typeof next === "function"
            ? (next as (current: T | null) => T | null)(currentData)
            : next,
        };
      }),
    [resourceKey],
  );
  const reload = useCallback(() => setRevision((v) => v + 1), []);
  useEffect(() => {
    if (!path) {
      setData(null);
      setError("");
      setLoading(false);
      return;
    }
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
  }, [path, revision, interval, scopeKey, setData]);
  return { data, error, loading, reload, setData };
}
export type Row = Record<string, unknown>;
export function text(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
