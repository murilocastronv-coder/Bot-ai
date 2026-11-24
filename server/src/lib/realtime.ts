import type { WebSocket } from "ws";
const subs = new Map<string, Set<WebSocket>>();
export function subscribe(key: string, ws: WebSocket) {
  if (!subs.has(key)) subs.set(key, new Set());
  subs.get(key)!.add(ws);
  ws.on("close", () => subs.get(key)?.delete(ws));
}
export function publish(key: string, event: unknown) {
  const data = JSON.stringify(event);
  for (const ws of subs.get(key) ?? []) if (ws.readyState === 1) ws.send(data);
}
export const bizKey = (businessId: string) => `biz:${businessId}`;
export const convKey = (conversationId: string) => `conv:${conversationId}`;
