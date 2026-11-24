import { Router } from "express";
import { z } from "zod";
import { prisma } from "../lib/db.js";
import { asyncH } from "../lib/auth.js";
import { monthStart, PLANS } from "../lib/plans.js";
import { getStripe } from "../services/stripe.js";

export const adminRouter = Router();

adminRouter.get("/stats", asyncH(async (_req, res) => {
  const since = monthStart();
  const [total, byPlan, usage, errors24h] = await Promise.all([
    prisma.business.count(),
    prisma.business.groupBy({ by: ["plan"], where: { subscriptionStatus: { in: ["active", "trialing"] }, stripeSubscriptionId: { not: null } }, _count: true }),
    prisma.usageRecord.aggregate({ where: { createdAt: { gte: since } }, _count: true, _sum: { costMicroUsd: true } }),
    prisma.errorLog.count({ where: { createdAt: { gte: new Date(Date.now() - 86400000) } } }),
  ]);
  const mrr = byPlan.reduce((s, p) => s + PLANS[p.plan].priceEur * p._count, 0);
  const t0 = Date.now(); await prisma.$queryRaw`SELECT 1`; const dbMs = Date.now() - t0;
  res.json({
    businesses: total, activeSubscriptions: byPlan.reduce((s, p) => s + p._count, 0), byPlan: Object.fromEntries(byPlan.map((p) => [p.plan, p._count])),
    mrrEur: Math.round(mrr * 100) / 100, aiResponsesMonth: usage._count, aiCostUsdMonth: (usage._sum.costMicroUsd ?? 0) / 1e6, errors24h,
    server: { uptimeSec: Math.round(process.uptime()), rssMb: Math.round(process.memoryUsage().rss / 1048576), dbLatencyMs: dbMs, node: process.version },
  });
}));

adminRouter.get("/revenue", asyncH(async (_req, res) => {
  const stripe = getStripe();
  if (!stripe) return res.status(503).json({ error: "Stripe não configurado" });
  const since = Math.floor(monthStart().getTime() / 1000);
  let total = 0;
  for await (const inv of stripe.invoices.list({ status: "paid", created: { gte: since }, limit: 100 })) total += inv.amount_paid;
  res.json({ month: new Date().toISOString().slice(0, 7), paidEur: total / 100 });
}));

adminRouter.get("/businesses", asyncH(async (_req, res) => {
  const since = monthStart();
  const list = await prisma.business.findMany({ orderBy: { createdAt: "desc" }, take: 500, select: { id: true, name: true, plan: true, subscriptionStatus: true, blocked: true, createdAt: true, users: { select: { email: true } } } });
  const usage = await prisma.usageRecord.groupBy({ by: ["businessId"], where: { createdAt: { gte: since } }, _count: true, _sum: { costMicroUsd: true } });
  const u = new Map(usage.map((x) => [x.businessId, x]));
  res.json(list.map((b) => ({ ...b, aiResponsesMonth: u.get(b.id)?._count ?? 0, aiCostUsdMonth: (u.get(b.id)?._sum.costMicroUsd ?? 0) / 1e6 })));
}));

adminRouter.post("/businesses/:id/block", asyncH(async (req, res) => {
  const { blocked } = z.object({ blocked: z.boolean() }).parse(req.body);
  await prisma.business.update({ where: { id: req.params.id }, data: { blocked } });
  res.json({ ok: true });
}));

adminRouter.post("/businesses/:id/plan", asyncH(async (req, res) => {
  const { plan, trialDays } = z.object({ plan: z.enum(["FREE", "STARTER", "PROFESSIONAL", "BUSINESS"]), trialDays: z.number().int().min(0).max(90).optional() }).parse(req.body);
  await prisma.business.update({ where: { id: req.params.id }, data: { plan, ...(plan !== "FREE" ? { subscriptionStatus: "active" } : {}), ...(trialDays !== undefined ? { trialEndsAt: new Date(Date.now() + trialDays * 86400000) } : {}) } });
  res.json({ ok: true });
}));

adminRouter.get("/errors", asyncH(async (_req, res) => res.json(await prisma.errorLog.findMany({ orderBy: { createdAt: "desc" }, take: 200 }))));

/** Cupons promocionais = Coupon + Promotion Code no Stripe (aplicáveis no checkout). */
adminRouter.post("/coupons", asyncH(async (req, res) => {
  const d = z.object({ code: z.string().regex(/^[A-Z0-9_-]{3,30}$/), percentOff: z.number().min(1).max(100), durationMonths: z.number().int().min(1).max(24) }).parse(req.body);
  const stripe = getStripe();
  if (!stripe) return res.status(503).json({ error: "Stripe não configurado" });
  const coupon = await stripe.coupons.create({ percent_off: d.percentOff, duration: "repeating", duration_in_months: d.durationMonths, name: d.code });
  const promo = await stripe.promotionCodes.create({ code: d.code, promotion: { type: "coupon", coupon: coupon.id } } as any);
  res.json({ ok: true, id: promo.id, code: promo.code });
}));
