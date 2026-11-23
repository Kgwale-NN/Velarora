import { text } from "./useResource";

export function computerLabel(computerId: unknown, fallback?: unknown): string {
  const id = Number(computerId);
  return Number.isSafeInteger(id) && id > 0
    ? `PC number - ${id}`
    : text(fallback);
}
