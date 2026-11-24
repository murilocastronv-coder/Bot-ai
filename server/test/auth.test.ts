import { describe, expect, it } from "vitest";
import request from "supertest";
import { app, signup } from "./helpers.js";
import { prisma } from "../src/lib/db.js";
import { sentMails } from "../src/lib/mailer.js";

describe("autenticação", () => {
  it("cadastro exige verificação de e-mail antes do login e cria teste de 7 dias", async () => {
    const email = "nova@test.dev";
    await request(app).post("/api/auth/register").send({ name: "A", email, password: "senha-muito-segura", businessName: "X", template: "barber", acceptTerms: true }).expect(201);
    const r = await request(app).post("/api/auth/login").send({ email, password: "senha-muito-segura" });
    expect(r.status).toBe(403);
    expect(r.body.code).toBe("EMAIL_NOT_VERIFIED");
    const u = await prisma.user.findUniqueOrThrow({ where: { email }, include: { business: true } });
    expect(u.passwordHash).not.toContain("senha");
    expect(u.business!.trialEndsAt.getTime()).toBeGreaterThan(Date.now() + 6.9 * 86400000);
  });

  it("rejeita senha fraca, honeypot preenchido e e-mail duplicado", async () => {
    const base = { name: "A", email: "x@test.dev", password: "senha-muito-segura", businessName: "X", template: "barber", acceptTerms: true };
    await request(app).post("/api/auth/register").send({ ...base, password: "123" }).expect(400);
    await request(app).post("/api/auth/register").send({ ...base, website: "spam" }).expect(400);
    await request(app).post("/api/auth/register").send(base).expect(201);
    await request(app).post("/api/auth/register").send(base).expect(409);
  });

  it("login completo, /me e logout", async () => {
    const { agent } = await signup("me@test.dev");
    const me = await agent.get("/api/auth/me").expect(200);
    expect(me.body.email).toBe("me@test.dev");
    await agent.post("/api/auth/logout").expect(200);
    await agent.get("/api/auth/me").expect(401);
  });

  it("recuperação de senha com token de uso único", async () => {
    await signup("reset@test.dev");
    await request(app).post("/api/auth/forgot").send({ email: "reset@test.dev" }).expect(200);
    await request(app).post("/api/auth/forgot").send({ email: "naoexiste@test.dev" }).expect(200); // não revela
    const token = /token=([\w-]+)/.exec(sentMails.filter((m) => m.to === "reset@test.dev").pop()!.text)![1];
    await request(app).post("/api/auth/reset").send({ token, password: "nova-senha-segura" }).expect(200);
    await request(app).post("/api/auth/reset").send({ token, password: "outra-senha-segura" }).expect(400);
    await request(app).post("/api/auth/login").send({ email: "reset@test.dev", password: "nova-senha-segura" }).expect(200);
  });
});

describe("isolamento entre empresas", () => {
  it("empresa A não acessa nem altera dados da empresa B", async () => {
    const a = await signup("a@test.dev");
    const b = await signup("b@test.dev");
    const svc = await b.agent.post("/api/services").send({ name: "Corte", priceCents: 2000 }).expect(201);
    const contact = await prisma.contact.create({ data: { businessId: b.businessId, channel: "WIDGET", externalId: "s1", name: "Cliente B" } });
    expect((await a.agent.get("/api/services")).body).toEqual([]);
    expect((await a.agent.get("/api/contacts")).body).toEqual([]);
    await a.agent.put(`/api/services/${svc.body.id}`).send({ priceCents: 1 }).expect(404);
    await a.agent.delete(`/api/contacts/${contact.id}`).expect(404);
    await a.agent.get(`/api/contacts/${contact.id}/export`).expect(404);
    expect((await prisma.service.findUniqueOrThrow({ where: { id: svc.body.id } })).priceCents).toBe(2000);
  });

  it("admin geral é restrito a SUPERADMIN", async () => {
    const owner = await signup("owner@test.dev");
    await owner.agent.get("/api/admin/stats").expect(403);
    const admin = await signup("admin@test.dev");
    const s = await admin.agent.get("/api/admin/stats").expect(200);
    expect(s.body.businesses).toBe(2);
    await admin.agent.post(`/api/admin/businesses/${owner.businessId}/block`).send({ blocked: true }).expect(200);
    await request(app).post("/api/auth/login").send({ email: "owner@test.dev", password: "senha-muito-segura" }).expect(403);
  });
});
