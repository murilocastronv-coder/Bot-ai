import type { Business, Contact, Service } from "@prisma/client";
import { prisma } from "../lib/db.js";
import { PLANS } from "../lib/plans.js";
import { getTemplate } from "./templates.js";
import { formatInTz, weekdayKey, zonedToUtc, type OpeningHours } from "./time.js";

export const TOOL_DEFS = [
  { type: "function", function: { name: "save_contact_info", description: "Salva dados que o cliente informou voluntariamente.", parameters: { type: "object", properties: { name: { type: "string" }, phone: { type: "string" }, email: { type: "string" }, service_interest: { type: "string" }, marketing_consent: { type: "boolean", description: "true só se o cliente aceitou explicitamente receber mensagens comerciais" } } } } },
  { type: "function", function: { name: "create_quote_request", description: "Cria um pedido de orçamento para a equipe responder.", parameters: { type: "object", properties: { service_name: { type: "string" }, details: { type: "string" } }, required: ["service_name", "details"] } } },
  { type: "function", function: { name: "check_availability", description: "Lista horários livres em uma data (YYYY-MM-DD) para um serviço cadastrado.", parameters: { type: "object", properties: { date: { type: "string" }, service_name: { type: "string" } }, required: ["date", "service_name"] } } },
  { type: "function", function: { name: "create_booking", description: "Cria um agendamento confirmado. Use após check_availability e confirmação do cliente.", parameters: { type: "object", properties: { date: { type: "string" }, time: { type: "string", description: "HH:MM" }, service_name: { type: "string" }, customer_name: { type: "string" } }, required: ["date", "time", "service_name", "customer_name"] } } },
  { type: "function", function: { name: "list_bookings", description: "Lista os próximos agendamentos deste cliente.", parameters: { type: "object", properties: {} } } },
  { type: "function", function: { name: "cancel_booking", description: "Cancela um agendamento deste cliente.", parameters: { type: "object", properties: { booking_id: { type: "string" } }, required: ["booking_id"] } } },
  { type: "function", function: { name: "request_human", description: "Transfere a conversa para um atendente humano.", parameters: { type: "object", properties: { reason: { type: "string" } }, required: ["reason"] } } },
];

export interface ToolCtx { business: Business; contact: Contact; conversationId: string; services: Service[]; handoff: boolean }

const findService = (services: Service[], name: string) => {
  const n = name.toLowerCase().trim();
  return services.find((s) => s.name.toLowerCase() === n) ?? services.find((s) => s.name.toLowerCase().includes(n) || n.includes(s.name.toLowerCase()));
};

const bookingAllowed = (b: Business) => PLANS[b.plan].booking && getTemplate(b.template).usesBooking;

export function freeSlots(b: Business, day: string, durationMin: number, existing: { startsAt: Date; endsAt: Date }[]): string[] {
  const hours = (b.openingHours as OpeningHours)[weekdayKey(day, b.timezone) as keyof OpeningHours] ?? [];
  const out: string[] = [];
  const now = Date.now();
  for (const [open, close] of hours) {
    const end = zonedToUtc(day, close, b.timezone).getTime();
    for (let t = zonedToUtc(day, open, b.timezone).getTime(); t + durationMin * 60000 <= end; t += b.slotMinutes * 60000) {
      const tEnd = t + durationMin * 60000;
      if (t < now) continue;
      if (existing.some((e) => e.startsAt.getTime() < tEnd && e.endsAt.getTime() > t)) continue;
      const d = new Date(t);
      out.push(new Intl.DateTimeFormat("en-GB", { timeZone: b.timezone, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(d));
    }
  }
  return out;
}

async function bookingsOfDay(businessId: string, day: string, tz: string) {
  const from = zonedToUtc(day, "00:00", tz), to = new Date(from.getTime() + 86400000);
  return prisma.booking.findMany({ where: { businessId, status: "CONFIRMED", startsAt: { lt: to }, endsAt: { gt: from } } });
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/, TIME_RE = /^\d{2}:\d{2}$/;

/** Executa uma ferramenta SEMPRE limitada à empresa e ao contato da conversa atual. */
export async function runTool(name: string, rawArgs: string, ctx: ToolCtx): Promise<unknown> {
  let a: any = {};
  try { a = JSON.parse(rawArgs || "{}"); } catch { return { error: "argumentos inválidos" }; }
  const { business: b, contact } = ctx;
  const str = (v: unknown, max = 500) => (typeof v === "string" ? v.slice(0, max).trim() : "");

  switch (name) {
    case "save_contact_info": {
      const data: any = {};
      if (str(a.name)) data.name = str(a.name, 120);
      if (str(a.phone)) data.phone = str(a.phone, 40);
      if (str(a.email) && /^\S+@\S+\.\S+$/.test(a.email)) data.email = str(a.email, 200);
      if (str(a.service_interest)) data.serviceInterest = str(a.service_interest, 200);
      if (typeof a.marketing_consent === "boolean") { data.marketingConsent = a.marketing_consent; data.consentAt = new Date(); }
      if (contact.status === "NEW" && (data.phone || data.email || data.serviceInterest)) data.status = "LEAD";
      Object.assign(contact, await prisma.contact.update({ where: { id: contact.id }, data }));
      return { ok: true };
    }
    case "create_quote_request": {
      const q = await prisma.quoteRequest.create({ data: { businessId: b.id, contactId: contact.id, serviceName: str(a.service_name, 200), details: str(a.details, 2000) } });
      if (contact.status === "NEW") await prisma.contact.update({ where: { id: contact.id }, data: { status: "LEAD" } });
      return { ok: true, quote_id: q.id, message: "Pedido registrado; a equipe responderá." };
    }
    case "check_availability": {
      if (!bookingAllowed(b)) return { error: "Agendamento automático não disponível; ofereça pedido de orçamento ou atendente humano." };
      if (!DATE_RE.test(a.date)) return { error: "data deve ser YYYY-MM-DD" };
      const svc = findService(ctx.services.filter((s) => s.bookable), str(a.service_name));
      if (!svc) return { error: "serviço não encontrado ou não agendável", services: ctx.services.filter((s) => s.bookable).map((s) => s.name) };
      const slots = freeSlots(b, a.date, svc.durationMin, await bookingsOfDay(b.id, a.date, b.timezone));
      return { service: svc.name, date: a.date, free_slots: slots.slice(0, 16), note: slots.length ? undefined : "sem horários livres nesta data" };
    }
    case "create_booking": {
      if (!bookingAllowed(b)) return { error: "Agendamento automático não disponível." };
      if (!DATE_RE.test(a.date) || !TIME_RE.test(a.time)) return { error: "formato inválido" };
      const svc = findService(ctx.services.filter((s) => s.bookable), str(a.service_name));
      if (!svc) return { error: "serviço não encontrado" };
      const slots = freeSlots(b, a.date, svc.durationMin, await bookingsOfDay(b.id, a.date, b.timezone));
      if (!slots.includes(a.time)) return { error: "horário indisponível", free_slots: slots.slice(0, 10) };
      const startsAt = zonedToUtc(a.date, a.time, b.timezone);
      const bk = await prisma.booking.create({ data: { businessId: b.id, contactId: contact.id, serviceName: svc.name, startsAt, endsAt: new Date(startsAt.getTime() + svc.durationMin * 60000) } });
      await prisma.contact.update({ where: { id: contact.id }, data: { name: contact.name || str(a.customer_name, 120), status: "CUSTOMER", serviceInterest: svc.name } });
      return { ok: true, booking_id: bk.id, when: formatInTz(startsAt, b.timezone), service: svc.name };
    }
    case "list_bookings": {
      const list = await prisma.booking.findMany({ where: { businessId: b.id, contactId: contact.id, status: "CONFIRMED", startsAt: { gt: new Date() } }, orderBy: { startsAt: "asc" } });
      return list.map((x) => ({ booking_id: x.id, service: x.serviceName, when: formatInTz(x.startsAt, b.timezone) }));
    }
    case "cancel_booking": {
      const r = await prisma.booking.updateMany({ where: { id: str(a.booking_id, 60), businessId: b.id, contactId: contact.id, status: "CONFIRMED" }, data: { status: "CANCELLED" } });
      return r.count ? { ok: true } : { error: "agendamento não encontrado" };
    }
    case "request_human": {
      ctx.handoff = true;
      await prisma.conversation.update({ where: { id: ctx.conversationId }, data: { status: "HUMAN" } });
      return { ok: true, message: "Conversa transferida. Avise o cliente que um atendente responderá assim que possível." };
    }
    default: return { error: "ferramenta desconhecida" };
  }
}
