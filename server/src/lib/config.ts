function req(name: string, fallback?: string): string {
  const v = process.env[name] ?? fallback;
  if (v === undefined || v === "") throw new Error(`Variável de ambiente obrigatória ausente: ${name}`);
  return v;
}
const isProd = process.env.NODE_ENV === "production";

export const config = {
  isProd,
  port: Number(process.env.PORT ?? 3000),
  appUrl: (process.env.APP_URL || process.env.RENDER_EXTERNAL_URL || "http://localhost:3000").replace(/\/$/, ""),
  jwtSecret: req("JWT_SECRET", isProd ? undefined : "dev-only-jwt-secret-change-me"),
  // 32 bytes em base64 — criptografa tokens de Telegram/WhatsApp no banco
  encryptionKey: req("ENCRYPTION_KEY", isProd ? undefined : Buffer.alloc(32, 7).toString("base64")),
  // Qualquer API compatível com OpenAI: OpenAI, Groq (grátis), Google Gemini (grátis)…
  openaiApiKey: process.env.AI_API_KEY || process.env.OPENAI_API_KEY || "",
  openaiModel: process.env.AI_MODEL || process.env.OPENAI_MODEL || "gpt-4o-mini",
  openaiBaseUrl: (process.env.AI_BASE_URL || process.env.OPENAI_BASE_URL || "https://api.openai.com/v1").replace(/\/$/, ""),
  // custo estimado em micro-USD por 1M tokens (ajuste conforme a tabela oficial da OpenAI)
  costInPerMTok: Number(process.env.OPENAI_COST_IN_PER_MTOK_USD ?? 0.15),
  costOutPerMTok: Number(process.env.OPENAI_COST_OUT_PER_MTOK_USD ?? 0.6),
  stripeSecretKey: process.env.STRIPE_SECRET_KEY ?? "",
  stripeWebhookSecret: process.env.STRIPE_WEBHOOK_SECRET ?? "",
  stripePrices: {
    STARTER: process.env.STRIPE_PRICE_STARTER ?? "",
    PROFESSIONAL: process.env.STRIPE_PRICE_PROFESSIONAL ?? "",
    BUSINESS: process.env.STRIPE_PRICE_BUSINESS ?? "",
  },
  waVerifyToken: process.env.WHATSAPP_VERIFY_TOKEN ?? "",
  waAppSecret: process.env.WHATSAPP_APP_SECRET ?? "",
  graphApiVersion: process.env.META_GRAPH_VERSION ?? "v21.0",
  telegramApiBase: process.env.TELEGRAM_API_BASE ?? "https://api.telegram.org",
  smtpUrl: process.env.SMTP_URL ?? "",
  // "off" = contas já nascem verificadas (útil sem servidor de e-mail; menos proteção contra spam)
  emailVerification: (process.env.EMAIL_VERIFICATION ?? "on").toLowerCase() !== "off",
  mailFrom: process.env.MAIL_FROM ?? "SmartBusiness AI <no-reply@example.com>",
  superadminEmails: (process.env.SUPERADMIN_EMAILS ?? "").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean),
};
