import { prisma } from "./db.js";
export async function logError(source: string, err: unknown, businessId?: string) {
  const message = err instanceof Error ? `${err.message}` : String(err);
  console.error(`[${source}]`, message);
  try { await prisma.errorLog.create({ data: { source, message: message.slice(0, 2000), businessId } }); } catch { /* ignore */ }
}
