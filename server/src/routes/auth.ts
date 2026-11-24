import { Router } from "express";
import bcrypt from "bcryptjs";
import rateLimit from "express-rate-limit";
import { z } from "zod";
import { prisma } from "../lib/db.js";
import { asyncH, COOKIE, issueSession, requireAuth } from "../lib/auth.js";
import { config } from "../lib/config.js";
import { randomToken, sha256 } from "../lib/crypto.js";
import { sendMail } from "../lib/mailer.js";
import { TRIAL_DAYS } from "../lib/plans.js";
import { TEMPLATES } from "../agent/templates.js";

export const authRouter = Router();
const authLimiter = rateLimit({ windowMs: 15 * 60000, limit: config.isProd ? 20 : 1000, standardHeaders: true, legacyHeaders: false });

const password = z.string().min(10, "A senha deve ter pelo menos 10 caracteres").max(200);
const registerSchema = z.object({
  name: z.string().min(1).max(120), email: z.string().email().max(200), password,
  businessName: z.string().min(1).max(160), template: z.enum(TEMPLATES.map((t) => t.id) as [string, ...string[]]),
  acceptTerms: z.literal(true), website: z.string().max(0).optional(), // honeypot anti-spam
});

authRouter.post("/register", authLimiter, asyncH(async (req, res) => {
  const d = registerSchema.parse(req.body);
  const email = d.email.toLowerCase();
  if (await prisma.user.findUnique({ where: { email } })) return res.status(409).json({ error: "E-mail já cadastrado" });
  const token = randomToken();
  const business = await prisma.business.create({ data: {
    name: d.businessName, template: d.template, trialEndsAt: new Date(Date.now() + TRIAL_DAYS * 86400000),
    openingHours: { mon: [["09:00", "18:00"]], tue: [["09:00", "18:00"]], wed: [["09:00", "18:00"]], thu: [["09:00", "18:00"]], fri: [["09:00", "18:00"]] },
  } });
  await prisma.user.create({ data: {
    email, name: d.name, passwordHash: await bcrypt.hash(d.password, 12), businessId: business.id,
    ...(config.emailVerification ? { emailVerifyToken: sha256(token) } : { emailVerifiedAt: new Date() }),
    role: config.superadminEmails.includes(email) ? "SUPERADMIN" : "OWNER",
  } });
  if (!config.emailVerification) return res.status(201).json({ ok: true, verified: true, message: "Conta criada. Você já pode entrar." });
  await sendMail(email, "Confirme seu e-mail — SmartBusiness AI", `Olá ${d.name},\n\nConfirme seu e-mail abrindo o link:\n${config.appUrl}/api/auth/verify?token=${token}\n`);
  res.status(201).json({ ok: true, message: "Conta criada. Verifique seu e-mail para ativar o acesso." });
}));

authRouter.get("/verify", asyncH(async (req, res) => {
  const token = String(req.query.token ?? "");
  const user = token ? await prisma.user.findUnique({ where: { emailVerifyToken: sha256(token) } }) : null;
  if (!user) return res.redirect("/login?verified=0");
  await prisma.user.update({ where: { id: user.id }, data: { emailVerifiedAt: new Date(), emailVerifyToken: null } });
  res.redirect("/login?verified=1");
}));

authRouter.post("/login", authLimiter, asyncH(async (req, res) => {
  const { email, password: pw } = z.object({ email: z.string().email(), password: z.string().max(200) }).parse(req.body);
  const user = await prisma.user.findUnique({ where: { email: email.toLowerCase() }, include: { business: true } });
  if (!user || !(await bcrypt.compare(pw, user.passwordHash))) return res.status(401).json({ error: "E-mail ou senha inválidos" });
  if (!user.emailVerifiedAt) return res.status(403).json({ error: "Confirme seu e-mail antes de entrar", code: "EMAIL_NOT_VERIFIED" });
  if (user.business?.blocked) return res.status(403).json({ error: "Conta bloqueada. Contate o suporte." });
  issueSession(res, user.id);
  res.json({ ok: true });
}));

authRouter.post("/resend-verification", authLimiter, asyncH(async (req, res) => {
  const { email } = z.object({ email: z.string().email() }).parse(req.body);
  const user = await prisma.user.findUnique({ where: { email: email.toLowerCase() } });
  if (user && !user.emailVerifiedAt) {
    const token = randomToken();
    await prisma.user.update({ where: { id: user.id }, data: { emailVerifyToken: sha256(token) } });
    await sendMail(user.email, "Confirme seu e-mail — SmartBusiness AI", `${config.appUrl}/api/auth/verify?token=${token}`);
  }
  res.json({ ok: true });
}));

authRouter.post("/logout", (_req, res) => { res.clearCookie(COOKIE, { path: "/" }); res.json({ ok: true }); });

authRouter.post("/forgot", authLimiter, asyncH(async (req, res) => {
  const { email } = z.object({ email: z.string().email() }).parse(req.body);
  const user = await prisma.user.findUnique({ where: { email: email.toLowerCase() } });
  if (user) {
    const token = randomToken();
    await prisma.user.update({ where: { id: user.id }, data: { resetTokenHash: sha256(token), resetTokenExpires: new Date(Date.now() + 3600000) } });
    await sendMail(user.email, "Redefinição de senha — SmartBusiness AI", `Para redefinir sua senha (válido por 1 hora):\n${config.appUrl}/reset?token=${token}\n\nSe não foi você, ignore este e-mail.`);
  }
  res.json({ ok: true }); // resposta idêntica para não revelar se o e-mail existe
}));

authRouter.post("/reset", authLimiter, asyncH(async (req, res) => {
  const { token, password: pw } = z.object({ token: z.string().min(10), password }).parse(req.body);
  const user = await prisma.user.findUnique({ where: { resetTokenHash: sha256(token) } });
  if (!user || !user.resetTokenExpires || user.resetTokenExpires < new Date()) return res.status(400).json({ error: "Link inválido ou expirado" });
  await prisma.user.update({ where: { id: user.id }, data: { passwordHash: await bcrypt.hash(pw, 12), resetTokenHash: null, resetTokenExpires: null, emailVerifiedAt: user.emailVerifiedAt ?? new Date() } });
  res.json({ ok: true });
}));

authRouter.get("/me", requireAuth, asyncH(async (req, res) => {
  const u = req.user!;
  res.json({ id: u.id, name: u.name, email: u.email, role: u.role, businessId: u.businessId });
}));
