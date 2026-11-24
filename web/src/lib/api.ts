export class ApiError extends Error { constructor(msg: string, public status: number, public code?: string) { super(msg); } }

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: opts.method ?? (opts.body ? "POST" : "GET"),
    headers: opts.body ? { "content-type": "application/json" } : undefined,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    credentials: "same-origin",
  });
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new ApiError((data as any)?.error ?? `Erro ${res.status}`, res.status, (data as any)?.code);
  return data as T;
}

export async function upload(path: string, file: File) {
  const fd = new FormData(); fd.append("file", file);
  const res = await fetch(`/api${path}`, { method: "POST", body: fd, credentials: "same-origin" });
  const data = await res.json();
  if (!res.ok) throw new ApiError(data.error ?? "Erro", res.status);
  return data;
}

export const eur = (cents: number | null | undefined) => cents == null ? "—" : (cents / 100).toLocaleString("fr-FR", { style: "currency", currency: "EUR" });
export const dt = (s: string | Date) => new Date(s).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
