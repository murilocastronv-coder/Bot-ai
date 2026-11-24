import { prisma } from "../lib/db.js";
import { telegram } from "./telegram.js";
import { PLANS } from "../lib/plans.js";
import { getTemplate } from "../agent/templates.js";
import { DAY_KEYS, type OpeningHours } from "../agent/time.js";
import { handleIncoming, openConversation, replyDirect } from "../agent/engine.js";

type L = "pt" | "fr" | "en" | "es";
type Action = "services" | "book" | "hours" | "quote" | "faq" | "human" | "menu";

const T: Record<L, Record<Action | "welcome" | "noServices" | "noFaq" | "humanOk" | "closed" | "onQuote" | "address" | "phone" | "bookAsk" | "quoteAsk", string>> = {
  pt: { services: "📋 Serviços e preços", book: "📅 Agendar horário", hours: "🕐 Horários e endereço", quote: "📝 Pedir orçamento", faq: "❓ Perguntas frequentes", human: "👤 Falar com atendente", menu: "📱 Menu",
    welcome: "Olá{n}! 👋 Sou o assistente virtual de *{b}*.\nEscolha uma opção no menu abaixo ou escreva sua pergunta.", noServices: "Ainda não temos serviços cadastrados aqui. Quer falar com um atendente?", noFaq: "Ainda não há perguntas frequentes cadastradas. Pode escrever sua dúvida!",
    humanOk: "Certo! Um atendente vai responder aqui assim que possível. 🙂", closed: "fechado", onQuote: "sob orçamento", address: "📍 Endereço", phone: "📞 Telefone", bookAsk: "Quero agendar um horário.", quoteAsk: "Quero pedir um orçamento." },
  fr: { services: "📋 Services et tarifs", book: "📅 Prendre rendez-vous", hours: "🕐 Horaires et adresse", quote: "📝 Demander un devis", faq: "❓ Questions fréquentes", human: "👤 Parler à un conseiller", menu: "📱 Menu",
    welcome: "Bonjour{n} ! 👋 Je suis l’assistant virtuel de *{b}*.\nChoisissez une option dans le menu ci-dessous ou écrivez votre question.", noServices: "Aucun service n’est encore enregistré. Voulez-vous parler à un conseiller ?", noFaq: "Aucune question fréquente pour l’instant. Écrivez-nous votre question !",
    humanOk: "Très bien ! Un conseiller vous répondra ici dès que possible. 🙂", closed: "fermé", onQuote: "sur devis", address: "📍 Adresse", phone: "📞 Téléphone", bookAsk: "Je voudrais prendre rendez-vous.", quoteAsk: "Je voudrais demander un devis." },
  en: { services: "📋 Services & prices", book: "📅 Book an appointment", hours: "🕐 Hours & address", quote: "📝 Request a quote", faq: "❓ FAQ", human: "👤 Talk to a person", menu: "📱 Menu",
    welcome: "Hi{n}! 👋 I'm the virtual assistant of *{b}*.\nPick an option from the menu below or type your question.", noServices: "No services are listed yet. Would you like to talk to a person?", noFaq: "No FAQs yet. Feel free to type your question!",
    humanOk: "Sure! A team member will reply here as soon as possible. 🙂", closed: "closed", onQuote: "on quote", address: "📍 Address", phone: "📞 Phone", bookAsk: "I'd like to book an appointment.", quoteAsk: "I'd like to request a quote." },
  es: { services: "📋 Servicios y precios", book: "📅 Reservar cita", hours: "🕐 Horario y dirección", quote: "📝 Pedir presupuesto", faq: "❓ Preguntas frecuentes", human: "👤 Hablar con una persona", menu: "📱 Menú",
    welcome: "¡Hola{n}! 👋 Soy el asistente virtual de *{b}*.\nElija una opción del menú o escriba su pregunta.", noServices: "Aún no hay servicios registrados. ¿Quiere hablar con una persona?", noFaq: "Aún no hay preguntas frecuentes. ¡Escriba su duda!",
    humanOk: "¡De acuerdo! Una persona le responderá aquí lo antes posible. 🙂", closed: "cerrado", onQuote: "según presupuesto", address: "📍 Dirección", phone: "📞 Teléfono", bookAsk: "Quiero reservar una cita.", quoteAsk: "Quiero pedir un presupuesto." },
};
const DAYS: Record<L, string[]> = {
  pt: ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"], fr: ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
  en: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], es: ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
};
const COMMANDS: Record<string, Action> = { "/start": "menu", "/menu": "menu", "/servicos": "services", "/agendar": "book", "/horarios": "hours", "/orcamento": "quote", "/faq": "faq", "/atendente": "human" };

export const asLang = (s: string | undefined): L => (["pt", "fr", "en", "es"].includes(s ?? "") ? (s as L) : "pt");

/** Reconhece um botão (em qualquer idioma) ou comando. */
export function parseMenuAction(text: string): Action | null {
  const cmd = text.trim().split(/[\s@]/)[0].toLowerCase();
  if (COMMANDS[cmd]) return COMMANDS[cmd];
  for (const l of Object.values(T)) for (const a of ["services", "book", "hours", "quote", "faq", "human", "menu"] as Action[]) if (l[a] === text.trim()) return a;
  return null;
}

/** Teclado fixo do Telegram (fica abaixo do campo de mensagem). */
export function menuKeyboard(lang: L, opts: { booking: boolean; quotes: boolean }) {
  const t = T[lang];
  const rows: string[][] = [[t.services, t.hours]];
  const second = [opts.booking ? t.book : null, opts.quotes ? t.quote : null].filter(Boolean) as string[];
  if (second.length) rows.push(second);
  rows.push([t.faq, t.human]);
  return { keyboard: rows.map((r) => r.map((text) => ({ text }))), resize_keyboard: true, is_persistent: true, input_field_placeholder: "…" };
}

export const BOT_COMMANDS = (lang: L) => {
  const t = T[lang]; const strip = (s: string) => s.replace(/^\S+\s/, "");
  return [
    { command: "menu", description: strip(t.menu) }, { command: "servicos", description: strip(t.services) }, { command: "agendar", description: strip(t.book) },
    { command: "horarios", description: strip(t.hours) }, { command: "orcamento", description: strip(t.quote) }, { command: "faq", description: strip(t.faq) },
    { command: "atendente", description: strip(t.human) },
  ];
};

const money = (cents: number) => (cents / 100).toLocaleString("fr-FR", { style: "currency", currency: "EUR" });

export interface MenuResult { reply: string; keyboard?: unknown; markdown?: boolean }

/**
 * Trata botões/comandos do menu. Serviços, horários e FAQ vêm do banco (sem IA);
 * "Agendar" e "Orçamento" iniciam o fluxo com o agente; "Atendente" transfere para humano.
 * Retorna null se a mensagem não for do menu.
 */
export async function handleMenu(businessId: string, chatId: string, text: string, tgLang: string, name: string): Promise<MenuResult | null> {
  const action = parseMenuAction(text);
  if (!action) return null;
  const b = await prisma.business.findUnique({ where: { id: businessId } });
  if (!b || b.blocked) return null;
  const tpl = getTemplate(b.template);
  const opts = { booking: tpl.usesBooking && PLANS[b.plan].booking, quotes: tpl.usesQuotes };
  // Menu sempre no idioma principal do negócio (1º da lista; padrão português),
  // não no idioma do celular do cliente. A IA continua respondendo no idioma que o cliente escrever.
  void tgLang;
  const lang = asLang(b.languages[0]);
  const t = T[lang];
  const kb = menuKeyboard(lang, opts);
  const base = { businessId, channel: "TELEGRAM" as const, externalId: chatId, name, languageHint: lang };

  if (action === "book" || action === "quote") {
    const out = await handleIncoming({ ...base, text: action === "book" ? t.bookAsk : t.quoteAsk });
    return out?.reply ? { reply: out.reply, keyboard: kb } : null;
  }

  const opened = await openConversation({ ...base, text: action === "menu" ? text.split(/\s/)[0] : (T[lang][action] ?? text) });
  if (!opened) return null;
  let reply = "";
  let handoff = false;
  if (action === "menu") {
    // /start volta a conversa para o idioma principal
    if (opened.contact.language !== lang) await prisma.contact.update({ where: { id: opened.contact.id }, data: { language: lang } });
    const first = name.split(" ")[0];
    reply = t.welcome.replace("{n}", first ? ` ${first}` : "").replace("{b}", b.name);
  } else if (action === "services") {
    const list = await prisma.service.findMany({ where: { businessId }, orderBy: { name: "asc" } });
    reply = list.length ? `${t.services}\n\n` + list.map((s) => `• ${s.name} — ${s.priceCents != null ? money(s.priceCents) : t.onQuote}${s.priceNote ? ` (${s.priceNote})` : ""}${s.description ? `\n   ${s.description}` : ""}`).join("\n") : t.noServices;
  } else if (action === "hours") {
    const h = b.openingHours as OpeningHours;
    reply = `${t.hours}\n\n` + DAY_KEYS.map((d, i) => `${DAYS[lang][i]}: ${(h?.[d] ?? []).map(([a, z]) => `${a}–${z}`).join(", ") || t.closed}`).join("\n");
    if (b.address) reply += `\n\n${t.address}: ${b.address}`;
    if (b.phone) reply += `\n${t.phone}: ${b.phone}`;
  } else if (action === "faq") {
    const faqs = await prisma.faq.findMany({ where: { businessId }, take: 10 });
    reply = faqs.length ? `${t.faq}\n\n` + faqs.map((f) => `❔ ${f.question}\n${f.answer}`).join("\n\n") : t.noFaq;
  } else if (action === "human") {
    reply = t.humanOk; handoff = true;
  }
  await replyDirect(opened.conv.id, businessId, reply, handoff);
  return { reply, keyboard: kb, markdown: action === "menu" };
}

/** Registra os comandos do botão "Menu" do Telegram no idioma principal do negócio. */
export async function registerBotCommands(token: string, primary: string = "pt") {
  await telegram.setMyCommands(token, BOT_COMMANDS(asLang(primary)));
  // remove versões por idioma do celular, para todos verem o idioma principal
  for (const l of ["pt", "fr", "en", "es"]) await telegram.deleteMyCommands(token, l);
}
