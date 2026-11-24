import express, { type NextFunction, type Request, type Response } from "express";
import cookieParser from "cookie-parser";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { ZodError } from "zod";
import { config } from "./lib/config.js";
import { prisma } from "./lib/db.js";
import { requireAuth, requireBusiness, requireSuperadmin } from "./lib/auth.js";
import { logError } from "./lib/log.js";
import { authRouter } from "./routes/auth.js";
import { businessRouter } from "./routes/business.js";
import { crmRouter } from "./routes/crm.js";
import { accountRouter } from "./routes/account.js";
import { billingRouter, stripeWebhook } from "./routes/billing.js";
import { webhooksRouter } from "./routes/webhooks.js";
import { widgetRouter } from "./routes/widget.js";
import { adminRouter } from "./routes/admin.js";
import { WIDGET_JS } from "./widget-script.js";
import { PLANS } from "./lib/plans.js";
import { TEMPLATES } from "./agent/templates.js";

const here = path.dirname(fileURLToPath(import.meta.url));

export function createApp() {
  const app = express();
  app.set("trust proxy", 1); // Render fica atrás de proxy
  app.disable("x-powered-by");
  app.use(helmet({ contentSecurityPolicy: { directives: { "default-src": ["'self'"], "script-src": ["'self'"], "style-src": ["'self'", "'unsafe-inline'"], "img-src": ["'self'", "data:"], "connect-src": ["'self'", "wss:", "ws:"], "frame-ancestors": ["'none'"], "upgrade-insecure-requests": config.isProd ? [] : null } } }));

  app.get("/health", async (_req, res) => {
    try { await prisma.$queryRaw`SELECT 1`; res.json({ ok: true }); } catch { res.status(503).json({ ok: false }); }
  });

  // Webhooks que exigem corpo bruto para verificação de assinatura
  app.post("/webhooks/stripe", express.raw({ type: "application/json", limit: "1mb" }), stripeWebhook);
  app.use("/webhooks/whatsapp", express.raw({ type: "*/*", limit: "2mb" }));

  app.use(express.json({ limit: "200kb" }));
  app.use(cookieParser());
  app.use("/webhooks", webhooksRouter);

  app.get("/widget.js", (_req, res) => {
    res.setHeader("content-type", "application/javascript; charset=utf-8");
    res.setHeader("cache-control", "public, max-age=300");
    res.setHeader("cross-origin-resource-policy", "cross-origin");
    res.send(WIDGET_JS);
  });
  app.use("/api/widget", widgetRouter);

  app.use("/api", rateLimit({ windowMs: 60000, limit: config.isProd ? 300 : 100000, standardHeaders: true, legacyHeaders: false }));
  app.use("/api/auth", authRouter);
  app.get("/api/public/plans", (_req, res) => res.json(Object.values(PLANS)));
  app.get("/api/public/templates", (_req, res) => res.json(TEMPLATES.map((t) => ({ id: t.id, label: t.label }))));
  app.get("/api/public/config", (_req, res) => res.json({ demoWidgetKey: process.env.DEMO_WIDGET_KEY || undefined, contactEmail: process.env.CONTACT_EMAIL || undefined }));
  app.use("/api/admin", requireAuth, requireSuperadmin, adminRouter);
  app.use("/api", requireAuth, requireBusiness, businessRouter, crmRouter, accountRouter, billingRouter);

  // Frontend React compilado
  const webDist = path.resolve(here, "../../web/dist");
  if (fs.existsSync(webDist)) {
    app.use(express.static(webDist, { index: false, maxAge: "1h" }));
    app.get(/^\/(?!api|webhooks).*/, (_req, res) => res.sendFile(path.join(webDist, "index.html")));
  }

  app.use((err: any, req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof ZodError) return res.status(400).json({ error: err.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ") });
    if (err?.code === "P2025") return res.status(404).json({ error: "Não encontrado" });
    const status = err?.status ?? 500;
    if (status >= 500) logError(`http ${req.method} ${req.path}`, err, req.businessId);
    res.status(status).json({ error: status >= 500 ? "Erro interno" : err.message });
  });
  return app;
}
