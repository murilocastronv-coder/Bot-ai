import Stripe from "stripe";
import type { Plan } from "@prisma/client";
import { config } from "../lib/config.js";
import { prisma } from "../lib/db.js";

let client: Stripe | null = null;
export function getStripe(): Stripe | null {
  if (!config.stripeSecretKey) return null;
  return (client ??= new Stripe(config.stripeSecretKey));
}

export function planFromPrice(priceId: string | undefined): Plan | null {
  const e = Object.entries(config.stripePrices).find(([, v]) => v && v === priceId);
  return (e?.[0] as Plan) ?? null;
}

/** Sincroniza o estado da assinatura com a empresa (fonte da verdade: Stripe). */
export async function syncSubscription(sub: Stripe.Subscription) {
  const customerId = typeof sub.customer === "string" ? sub.customer : sub.customer.id;
  const business = await prisma.business.findFirst({ where: { OR: [{ stripeSubscriptionId: sub.id }, { stripeCustomerId: customerId }, ...(sub.metadata?.businessId ? [{ id: sub.metadata.businessId }] : [])] } });
  if (!business) return null;
  const item = sub.items?.data?.[0] as any;
  const plan = planFromPrice(item?.price?.id);
  const periodEnd = (sub as any).current_period_end ?? item?.current_period_end;
  const ended = ["canceled", "incomplete_expired", "unpaid"].includes(sub.status);
  return prisma.business.update({ where: { id: business.id }, data: {
    stripeCustomerId: customerId,
    stripeSubscriptionId: ended ? null : sub.id,
    subscriptionStatus: sub.status,
    plan: ended ? "FREE" : (plan ?? business.plan),
    currentPeriodEnd: periodEnd ? new Date(periodEnd * 1000) : null,
  } });
}
