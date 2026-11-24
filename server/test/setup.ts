import { beforeEach, afterEach, vi } from "vitest";
process.env.DATABASE_URL = process.env.TEST_DATABASE_URL ?? "postgresql://postgres@localhost:5432/sb_test";
process.env.NODE_ENV = "test";
process.env.OPENAI_API_KEY = "sk-test";
process.env.APP_URL = "https://app.test";
process.env.WHATSAPP_VERIFY_TOKEN = "verify-me";
process.env.WHATSAPP_APP_SECRET = "meta-app-secret";
process.env.STRIPE_SECRET_KEY = "sk_test_dummy";
process.env.STRIPE_WEBHOOK_SECRET = "whsec_test_secret";
process.env.STRIPE_PRICE_STARTER = "price_starter";
process.env.STRIPE_PRICE_PROFESSIONAL = "price_pro";
process.env.STRIPE_PRICE_BUSINESS = "price_business";
process.env.SUPERADMIN_EMAILS = "admin@test.dev";

const { prisma } = await import("../src/lib/db.js");
beforeEach(async () => {
  const tables = await prisma.$queryRaw<{ tablename: string }[]>`SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> '_prisma_migrations'`;
  await prisma.$executeRawUnsafe(`TRUNCATE ${tables.map((t) => `"${t.tablename}"`).join(",")} CASCADE`);
});
afterEach(() => { vi.unstubAllGlobals(); });
