import crypto from "node:crypto";
import { describe, expect, it } from "vitest";
import request from "supertest";
import Stripe from "stripe";
import { app, mockFetch, openaiScript, setPlan, signup } from "./helpers.js";
import { prisma } from "../src/lib/db.js";
import { sendDueReminders } from "../src/services/reminders.js";

const BOT_TOKEN = "123456789:AAEhBOweik6ad9r_QXMENQjcrGbqCr4K-ra";

async function connectTelegram() {
  const s = await signup();
  await setPlan(s.businessId, "PROFESSIONAL");
  const calls = mockFetch({
    "/getMe": () => ({ ok: true, result: { id: 1, username: "salao_teste_bot" } }),
    "/setWebhook": () => ({ ok: true, result: true }),
    "/setMyCommands": () => ({ ok: true, result: true }),
  });
  const r = await s.agent.post("/api/channels/telegram").send({ token: BOT_TOKEN }).expect(200);
  return { ...s, calls, username: r.body.username };
}

describe("Telegram Bot API", () => {
  it("plano sem Telegram recusa a conexão", async () => {
    const { agent } = await signup();
    await agent.post("/api/channels/telegram").send({ token: BOT_TOKEN }).expect(402);
  });

  it("conecta o bot, registra webhook com secret_token e guarda o token criptografado", async () => {
    const { businessId, calls, username, agent } = await connectTelegram();
    expect(username).toBe("salao_teste_bot");
    const hook = calls.find((c) => c.url.endsWith("/setWebhook"))!;
    expect(hook.url).toContain(`/bot${BOT_TOKEN}/setWebhook`);
    expect(hook.body.url).toBe(`https://app.test/webhooks/telegram/${businessId}`);
    expect(hook.body.secret_token).toHaveLength(32);
    const b = await prisma.business.findUniqueOrThrow({ where: { id: businessId } });
    expect(b.telegramBotTokenEnc).not.toContain("AAEh");
    const pub = await agent.get("/api/business").expect(200);
    expect(JSON.stringify(pub.body)).not.toContain("telegramBotTokenEnc");
    expect(pub.body.telegramConnected).toBe(true);
  });

  it("webhook rejeita secret inválido e responde mensagens com a IA", async () => {
    const { businessId } = await connectTelegram();
    const b = await prisma.business.findUniqueOrThrow({ where: { id: businessId } });
    const update = { update_id: 99, message: { message_id: 1, chat: { id: 555, type: "private" }, from: { first_name: "Léa", language_code: "fr" }, text: "Bonjour, quels sont vos horaires ?" } };
    await request(app).post(`/webhooks/telegram/${businessId}`).set("x-telegram-bot-api-secret-token", "errado").send(update).expect(401);
    const calls = mockFetch({
      "api.openai.com": openaiScript([{ text: "Nous sommes ouverts du lundi au vendredi, 9h-18h." }]),
      "/sendChatAction": () => ({ ok: true, result: true }),
      "/sendMessage": () => ({ ok: true, result: {} }),
    });
    await request(app).post(`/webhooks/telegram/${businessId}`).set("x-telegram-bot-api-secret-token", b.telegramWebhookSecret!).send(update).expect(200);
    await expect.poll(() => calls.find((c) => c.url.endsWith("/sendMessage")), { timeout: 5000 }).toBeTruthy();
    const sent = calls.find((c) => c.url.endsWith("/sendMessage"))!;
    expect(sent.body).toMatchObject({ chat_id: "555", text: expect.stringContaining("lundi") });
    const contact = await prisma.contact.findFirstOrThrow({ where: { businessId } });
    expect(contact).toMatchObject({ channel: "TELEGRAM", name: "Léa", language: "fr" });
    // update duplicado (retry do Telegram) não gera segunda resposta
    await request(app).post(`/webhooks/telegram/${businessId}`).set("x-telegram-bot-api-secret-token", b.telegramWebhookSecret!).send(update).expect(200);
    await new Promise((r) => setTimeout(r, 300));
    expect(calls.filter((c) => c.url.endsWith("/sendMessage"))).toHaveLength(1);
  });

  it("lembrete de agendamento é enviado uma única vez pelo Telegram", async () => {
    const { businessId } = await connectTelegram();
    const contact = await prisma.contact.create({ data: { businessId, channel: "TELEGRAM", externalId: "777", language: "pt" } });
    await prisma.conversation.create({ data: { businessId, contactId: contact.id, channel: "TELEGRAM" } });
    await prisma.booking.create({ data: { businessId, contactId: contact.id, serviceName: "Corte", startsAt: new Date(Date.now() + 2 * 3600000), endsAt: new Date(Date.now() + 3 * 3600000) } });
    const calls = mockFetch({ "/sendMessage": () => ({ ok: true, result: {} }) });
    expect(await sendDueReminders()).toBe(1);
    expect(await sendDueReminders()).toBe(0);
    expect(calls[0].body.text).toContain("Lembrete");
  });
});

describe("menu do Telegram", () => {
  const send = async (businessId: string, secret: string, text: string, id: number) =>
    request(app).post(`/webhooks/telegram/${businessId}`).set("x-telegram-bot-api-secret-token", secret)
      .send({ update_id: id, message: { message_id: id, chat: { id: 4242, type: "private" }, from: { first_name: "Ana Paula", language_code: "pt" }, text } }).expect(200);

  it("/start mostra boas-vindas + teclado; botões respondem do banco sem IA; atendente transfere", async () => {
    const { businessId, agent } = await connectTelegram();
    await agent.post("/api/services").send({ name: "Corte", priceCents: 2500, durationMin: 30 }).expect(201);
    await agent.post("/api/services").send({ name: "Coloração", priceCents: null }).expect(201);
    await agent.post("/api/faqs").send({ question: "Aceitam cartão?", answer: "Sim, todos." }).expect(201);
    const b = await prisma.business.findUniqueOrThrow({ where: { id: businessId } });
    const calls = mockFetch({
      "api.openai.com": () => { throw new Error("menu não deve usar IA"); },
      "/sendChatAction": () => ({ ok: true, result: true }),
      "/sendMessage": () => ({ ok: true, result: {} }),
    });
    const sent = () => calls.filter((c) => c.url.endsWith("/sendMessage")).map((c) => c.body);
    await send(businessId, b.telegramWebhookSecret!, "/start", 1);
    await expect.poll(() => sent().length, { timeout: 5000 }).toBe(1);
    expect(sent()[0].text).toContain("Ana");
    expect(sent()[0].text).toContain("Salão Teste");
    const keys = sent()[0].reply_markup.keyboard.flat().map((k: any) => k.text);
    expect(keys).toEqual(expect.arrayContaining(["📋 Serviços e preços", "🕐 Horários e endereço", "❓ Perguntas frequentes", "👤 Falar com atendente", "📅 Agendar horário"]));

    await send(businessId, b.telegramWebhookSecret!, "📋 Serviços e preços", 2);
    await expect.poll(() => sent().length, { timeout: 5000 }).toBe(2);
    expect(sent()[1].text).toMatch(/Corte — 25,00/);
    expect(sent()[1].text).toContain("Coloração — sob orçamento");

    await send(businessId, b.telegramWebhookSecret!, "🕐 Horários e endereço", 3);
    await expect.poll(() => sent().length, { timeout: 5000 }).toBe(3);
    expect(sent()[2].text).toContain("Seg: 09:00–18:00");
    expect(sent()[2].text).toContain("Dom: fechado");

    await send(businessId, b.telegramWebhookSecret!, "/faq", 4);
    await expect.poll(() => sent().length, { timeout: 5000 }).toBe(4);
    expect(sent()[3].text).toContain("Aceitam cartão?");

    await send(businessId, b.telegramWebhookSecret!, "👤 Falar com atendente", 5);
    await expect.poll(() => sent().length, { timeout: 5000 }).toBe(5);
    const conv = await prisma.conversation.findFirstOrThrow({ where: { businessId }, include: { messages: true } });
    expect(conv.status).toBe("HUMAN");
    expect(conv.messages).toHaveLength(10); // 5 do cliente + 5 respostas no histórico
    expect(calls.some((c) => c.url.includes("openai"))).toBe(false);
  });

  it("botão Agendar inicia o fluxo com o agente de IA", async () => {
    const { businessId } = await connectTelegram();
    const b = await prisma.business.findUniqueOrThrow({ where: { id: businessId } });
    const calls = mockFetch({
      "api.openai.com": openaiScript([{ text: "Claro! Para qual serviço e dia?" }]),
      "/sendChatAction": () => ({ ok: true, result: true }),
      "/sendMessage": () => ({ ok: true, result: {} }),
    });
    await send(businessId, b.telegramWebhookSecret!, "📅 Agendar horário", 10);
    await expect.poll(() => calls.find((c) => c.url.endsWith("/sendMessage")), { timeout: 5000 }).toBeTruthy();
    const ai = calls.find((c) => c.url.includes("openai"))!;
    expect(ai.body.messages.at(-1).content).toBe("Quero agendar um horário.");
    expect(calls.find((c) => c.url.endsWith("/sendMessage"))!.body.reply_markup).toBeTruthy();
  });
});

describe("WhatsApp Business Cloud API", () => {
  const sign = (raw: string) => "sha256=" + crypto.createHmac("sha256", "meta-app-secret").update(raw).digest("hex");

  it("verificação do webhook (hub.challenge)", async () => {
    await request(app).get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=errado&hub.challenge=42").expect(403);
    const r = await request(app).get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=verify-me&hub.challenge=42").expect(200);
    expect(r.text).toBe("42");
  });

  it("conecta número, valida assinatura X-Hub-Signature-256 e responde", async () => {
    const { agent, businessId } = await signup();
    await setPlan(businessId, "STARTER");
    mockFetch({ "graph.facebook.com": () => ({ display_phone_number: "+33 6 00 00 00 00", verified_name: "Salão" }) });
    await agent.post("/api/channels/whatsapp").send({ phoneNumberId: "1234567890", accessToken: "EAAG-token-de-teste-longo-1234567890" }).expect(200);
    const payload = JSON.stringify({ object: "whatsapp_business_account", entry: [{ changes: [{ value: { metadata: { phone_number_id: "1234567890" }, contacts: [{ wa_id: "33611111111", profile: { name: "Marc" } }], messages: [{ id: "wamid.1", from: "33611111111", type: "text", text: { body: "Hello, what time do you open?" } }] } }] }] });
    await request(app).post("/webhooks/whatsapp").set("content-type", "application/json").set("x-hub-signature-256", "sha256=bad").send(payload).expect(401);
    const calls = mockFetch({ "api.openai.com": openaiScript([{ text: "We open at 9am." }]), "graph.facebook.com": () => ({ messages: [{ id: "wamid.out" }] }) });
    await request(app).post("/webhooks/whatsapp").set("content-type", "application/json").set("x-hub-signature-256", sign(payload)).send(payload).expect(200);
    await expect.poll(() => calls.find((c) => c.url.includes("/messages")), { timeout: 5000 }).toBeTruthy();
    const out = calls.find((c) => c.url.includes("/1234567890/messages"))!;
    expect(out.body).toMatchObject({ messaging_product: "whatsapp", to: "33611111111", text: { body: "We open at 9am." } });
    const c = await prisma.contact.findFirstOrThrow({ where: { businessId } });
    expect(c).toMatchObject({ name: "Marc", phone: "+33611111111", language: "en" });
  });
});

describe("Stripe", () => {
  const stripe = new Stripe("sk_test_dummy");
  const send = (event: object, secret = "whsec_test_secret") => {
    const payload = JSON.stringify(event);
    const header = stripe.webhooks.generateTestHeaderString({ payload, secret });
    return request(app).post("/webhooks/stripe").set("content-type", "application/json").set("stripe-signature", header).send(payload);
  };
  const subEvent = (id: string, businessId: string, status: string, price: string, type = "customer.subscription.updated") => ({
    id, object: "event", type, data: { object: { id: "sub_1", object: "subscription", customer: "cus_1", status, metadata: { businessId }, items: { data: [{ price: { id: price }, current_period_end: Math.floor(Date.now() / 1000) + 30 * 86400 }] } } },
  });

  it("rejeita assinatura inválida, ativa plano, é idempotente e volta ao FREE ao cancelar", async () => {
    const { businessId, agent } = await signup();
    await send(subEvent("evt_0", businessId, "active", "price_pro"), "whsec_errado").expect(400);
    await send(subEvent("evt_1", businessId, "active", "price_pro")).expect(200);
    let b = await prisma.business.findUniqueOrThrow({ where: { id: businessId } });
    expect(b).toMatchObject({ plan: "PROFESSIONAL", subscriptionStatus: "active", stripeSubscriptionId: "sub_1", stripeCustomerId: "cus_1" });
    const dup = await send(subEvent("evt_1", businessId, "active", "price_pro")).expect(200);
    expect(dup.body.duplicate).toBe(true);
    const billing = await agent.get("/api/business").expect(200);
    expect(billing.body.planDef.aiResponses).toBe(2000);
    await send(subEvent("evt_2", businessId, "canceled", "price_pro", "customer.subscription.deleted")).expect(200);
    b = await prisma.business.findUniqueOrThrow({ where: { id: businessId } });
    expect(b).toMatchObject({ plan: "FREE", stripeSubscriptionId: null, subscriptionStatus: "canceled" });
  });

  it("pagamento recusado (past_due) suspende a IA", async () => {
    const { businessId, agent } = await signup();
    await send(subEvent("evt_3", businessId, "past_due", "price_starter")).expect(200);
    const r = await agent.get("/api/business");
    expect(r.body.planActive).toBe(false);
  });
});

describe("CRM e RGPD", () => {
  it("exporta CSV sem injeção de fórmulas e apaga dados do cliente", async () => {
    const { agent, businessId } = await signup();
    const c = await prisma.contact.create({ data: { businessId, channel: "WIDGET", externalId: "abc", name: "=HYPERLINK(\"x\")", email: "c@x.com", marketingConsent: true } });
    const csv = await agent.get("/api/contacts.csv").expect(200);
    expect(csv.headers["content-type"]).toContain("text/csv");
    expect(csv.text).toContain(`"'=HYPERLINK(""x"")"`);
    expect(csv.text).toContain('"sim"');
    await agent.delete(`/api/contacts/${c.id}`).expect(200);
    expect(await prisma.contact.count()).toBe(0);
  });

  it("exclusão de conta exige senha e remove tudo", async () => {
    const { agent, businessId } = await signup();
    await agent.get("/api/account/export").expect(200);
    await agent.delete("/api/account").send({ password: "errada" }).expect(401);
    await agent.delete("/api/account").send({ password: "senha-muito-segura" }).expect(200);
    expect(await prisma.business.findUnique({ where: { id: businessId } })).toBeNull();
    expect(await prisma.user.count()).toBe(0);
  });
});
