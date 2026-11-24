import { Router, type Request, type Response } from "express";
import { z } from "zod";
import { prisma } from "../lib/db.js";
import { asyncH } from "../lib/auth.js";
import { config } from "../lib/config.js";
import { logError } from "../lib/log.js";
import { PLANS } from "../lib/plans.js";
import { getStripe, syncSubscription } from "../services/stripe.js";

export const billingRouter = Router();

billingRouter.get("/billing/plans", (_req, res) => res.json(Object.values(PLANS)));

billingRouter.post("/billing/checkout", asyncH(async (req, res) => {
  const { plan } = z.object({ plan: z.enum(["STARTER", "PROFESSIONAL", "BUSINESS"]) }).parse(req.body);
  const stripe = getStripe();
  const price = config.stripePrices[plan];
  if (!stripe || !price) return res.status(503).json({ error: "Pagamentos ainda não configurados (STRIPE_SECRET_KEY / STRIPE_PRICE_*)" });
  const b = await prisma.business.findUniqueOrThrow({ where: { id: req.businessId } });
  if (b.stripeSubscriptionId) return res.status(409).json({ error: "Já existe uma assinatura. Use 'Gerenciar assinatura' para trocar de plano." });
  let customer = b.stripeCustomerId;
  if (!customer) {
    customer = (await stripe.customers.create({ email: req.user!.email, name: b.name, metadata: { businessId: b.id } })).id;
    await prisma.business.update({ where: { id: b.id }, data: { stripeCustomerId: customer } });
  }
  const session = await stripe.checkout.sessions.create({
    mode: "subscription", customer, line_items: [{ price, quantity: 1 }],
    allow_promotion_codes: true, // cupons promocionais criados no painel Stripe
    client_reference_id: b.id, metadata: { businessId: b.id, plan },
    subscription_data: { metadata: { businessId: b.id } },
    success_url: `${config.appUrl}/app/billing?status=success`, cancel_url: `${config.appUrl}/app/billing?status=cancel`,
  });
  res.json({ url: session.url });
}));

billingRouter.post("/billing/portal", asyncH(async (req, res) => {
  const stripe = getStripe();
  const b = await prisma.business.findUniqueOrThrow({ where: { id: req.businessId } });
  if (!stripe || !b.stripeCustomerId) return res.status(400).json({ error: "Nenhuma assinatura Stripe encontrada" });
  const s = await stripe.billingPortal.sessions.create({ customer: b.stripeCustomerId, return_url: `${config.appUrl}/app/billing` });
  res.json({ url: s.url });
}));

/** Webhook Stripe com verificação de assinatura e idempotência. Corpo bruto obrigatório. */
export async function stripeWebhook(req: Request, res: Response) {
  const stripe = getStripe();
  if (!stripe || !config.stripeWebhookSecret) return res.status(503).send("Stripe não configurado");
  let event;
  try { event = stripe.webhooks.constructEvent(req.body as Buffer, String(req.headers["stripe-signature"] ?? ""), config.stripeWebhookSecret); }
  catch (e) { return res.status(400).send(`Assinatura inválida: ${(e as Error).message}`); }
  try {
    await prisma.processedWebhook.create({ data: { id: `stripe:${event.id}` } });
  } catch { return res.json({ received: true, duplicate: true }); }
  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const s = event.data.object;
        if (s.mode === "subscription" && s.subscription) {
          const sub = await stripe.subscriptions.retrieve(typeof s.subscription === "string" ? s.subscription : s.subscription.id);
          await syncSubscription(sub);
        }
        break;
      }
      case "customer.subscription.created":
      case "customer.subscription.updated":
      case "customer.subscription.deleted":
        await syncSubscription(event.data.object);
        break;
      case "invoice.payment_failed":
        await logError("stripe", `Pagamento falhou: ${event.data.object.customer}`);
        break;
    }
    res.json({ received: true });
  } catch (e) {
    await prisma.processedWebhook.delete({ where: { id: `stripe:${event.id}` } }).catch(() => undefined);
    await logError("stripe-webhook", e);
    res.status(500).send("erro");
  }
}
