let csrf = "";
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch("/api" + path, {
    ...options,
    credentials: "same-origin",
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(options.method && options.method !== "GET"
        ? { "X-CSRF-Token": csrf }
        : {}),
      ...options.headers,
    },
  });
  const data = await response
    .json()
    .catch(() => ({ detail: "The server returned an unexpected response." }));
  if (!response.ok)
    throw new ApiError(
      response.status,
      typeof data.detail === "string"
        ? data.detail
        : "Please check the form and try again.",
    );
  if (data.csrf) csrf = data.csrf;
  return data;
}
export const errorText = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";

export const adminApi = <T>(path: string, options: RequestInit = {}) =>
  api<T>("/admin" + path, options);
export const json = (method: string, value: unknown = {}) => ({
  method,
  body: JSON.stringify(value),
});
export async function download(path: string, name: string) {
  const response = await fetch("/api" + path, { credentials: "same-origin" });
  if (!response.ok) throw new Error("The download could not be completed.");
  saveBlob(await response.blob(), name);
}
export function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
