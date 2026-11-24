import type { Plan, Channel } from "@prisma/client";

export interface PlanDef {
  id: Plan; name: string; priceEur: number; aiResponses: number; maxUsers: number;
  channels: Channel[]; crm: "basic" | "full"; booking: boolean;
}

export const PLANS: Record<Plan, PlanDef> = {
  FREE:         { id: "FREE", name: "Gratuito", priceEur: 0, aiResponses: 50, maxUsers: 1, channels: ["WIDGET"], crm: "basic", booking: false },
  STARTER:      { id: "STARTER", name: "Starter", priceEur: 19.9, aiResponses: 500, maxUsers: 1, channels: ["WIDGET", "WHATSAPP"], crm: "basic", booking: false },
  PROFESSIONAL: { id: "PROFESSIONAL", name: "Professional", priceEur: 49.9, aiResponses: 2000, maxUsers: 3, channels: ["WIDGET", "WHATSAPP", "TELEGRAM"], crm: "full", booking: true },
  BUSINESS:     { id: "BUSINESS", name: "Business", priceEur: 99.9, aiResponses: 5000, maxUsers: 20, channels: ["WIDGET", "WHATSAPP", "TELEGRAM"], crm: "full", booking: true },
};

export const TRIAL_DAYS = 7;

export function monthStart(d = new Date()) { return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1)); }

/** Plano FREE só funciona durante o teste de 7 dias; planos pagos só com assinatura ativa. */
export function planIsActive(b: { plan: Plan; trialEndsAt: Date; subscriptionStatus: string }) {
  if (b.plan === "FREE") return b.trialEndsAt.getTime() > Date.now();
  return ["active", "trialing"].includes(b.subscriptionStatus);
}
