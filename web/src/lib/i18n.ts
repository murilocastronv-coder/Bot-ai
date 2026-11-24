export type Lang = "pt" | "fr" | "en" | "es";
export const LANGS: { id: Lang; label: string }[] = [
  { id: "fr", label: "Français" }, { id: "pt", label: "Português" }, { id: "en", label: "English" }, { id: "es", label: "Español" },
];

type Dict = {
  nav: { features: string; pricing: string; faq: string; login: string; trial: string };
  hero: { title: string; sub: string; cta: string; note: string };
  features: { title: string; items: [string, string][] };
  how: { title: string; steps: string[] };
  demo: { title: string; sub: string; illustrative: string; open: string };
  pricing: { title: string; month: string; choose: string; plans: Record<string, string[]>; note: string };
  faq: { title: string; items: [string, string][] };
  contact: { title: string; sub: string; cta: string };
  footer: { privacy: string; terms: string };
};

const pt: Dict = {
  nav: { features: "Recursos", pricing: "Planos", faq: "Perguntas", login: "Entrar", trial: "Teste grátis" },
  hero: { title: "Um atendente de IA para a sua empresa, 24 horas por dia", sub: "Responde clientes no WhatsApp, Telegram e no seu site, agenda horários, registra orçamentos e passa para você quando precisar — usando apenas as informações que você autorizar.", cta: "Começar teste grátis de 7 dias", note: "Sem cartão de crédito no teste." },
  features: { title: "Tudo o que sua empresa precisa para atender melhor", items: [
    ["Atendimento 24/7", "O agente responde mesmo quando você está offline."],
    ["Agenda automática", "Consulta horários livres, agenda, remarca, cancela e envia lembretes."],
    ["Orçamentos e potenciais clientes", "Coleta os dados certos e registra no CRM."],
    ["Sem inventar nada", "Preços, serviços e horários vêm só do que você cadastrar."],
    ["4 idiomas", "Detecta e responde em francês, português, inglês e espanhol."],
    ["Humano quando precisar", "Assuma qualquer conversa pelo painel com um toque."],
  ] },
  how: { title: "Pronto em poucos minutos", steps: ["Crie sua conta e escolha o tipo de negócio", "Informe serviços, preços, horários e perguntas frequentes", "Conecte o site, WhatsApp ou Telegram"] },
  demo: { title: "Veja o agente em ação", sub: "Converse com um agente de demonstração configurado para um salão fictício.", illustrative: "Exemplo ilustrativo de conversa (não é uma conversa real).", open: "Abrir chat de demonstração" },
  pricing: { title: "Planos simples", month: "/mês", choose: "Escolher", note: "Preços em euros, IVA conforme sua localização. Cancele quando quiser.", plans: {
    FREE: ["Teste de 7 dias", "50 respostas de IA", "Chat no site"],
    STARTER: ["500 respostas de IA/mês", "1 agente personalizado", "WhatsApp", "Painel básico"],
    PROFESSIONAL: ["2.000 respostas de IA/mês", "WhatsApp e Telegram", "CRM completo", "Agendamento automático", "Relatórios"],
    BUSINESS: ["5.000 respostas de IA/mês", "Até 20 usuários", "Todas as integrações disponíveis", "Suporte prioritário"],
  } },
  faq: { title: "Perguntas frequentes", items: [
    ["A IA pode inventar preços?", "Não. O agente é instruído a usar apenas os dados cadastrados. Se não souber, ele oferece transferir para você ou registrar um pedido de orçamento."],
    ["Preciso de conhecimento técnico?", "Não. Você preenche formulários simples. Para o site, basta colar uma linha de código."],
    ["Como funciona o WhatsApp?", "Usamos a API oficial WhatsApp Business Cloud da Meta. É preciso ter uma conta Meta Business verificada e um número dedicado."],
    ["E o Telegram?", "Você cria um bot gratuito no @BotFather e cola o token no painel. A conexão é feita automaticamente."],
    ["Meus dados ficam seguros?", "Cada empresa tem dados isolados, credenciais criptografadas e você pode exportar ou excluir tudo a qualquer momento (RGPD)."],
    ["O que acontece se eu atingir o limite?", "O agente envia uma mensagem padrão e passa a conversa para atendimento humano, sem custos extras."],
  ] },
  contact: { title: "Fale com a equipe comercial", sub: "Dúvidas sobre planos, volume ou integrações?", cta: "Enviar e-mail" },
  footer: { privacy: "Política de privacidade", terms: "Termos de uso" },
};

const fr: Dict = {
  nav: { features: "Fonctionnalités", pricing: "Tarifs", faq: "FAQ", login: "Connexion", trial: "Essai gratuit" },
  hero: { title: "Un assistant IA pour votre entreprise, 24h/24", sub: "Il répond à vos clients sur WhatsApp, Telegram et votre site, prend les rendez-vous, enregistre les demandes de devis et vous passe la main si besoin — uniquement avec les informations que vous autorisez.", cta: "Commencer l’essai gratuit de 7 jours", note: "Sans carte bancaire pendant l’essai." },
  features: { title: "Tout ce qu’il faut pour mieux servir vos clients", items: [
    ["Disponible 24h/24, 7j/7", "L’agent répond même quand vous êtes hors ligne."],
    ["Agenda automatique", "Vérifie les créneaux, réserve, modifie, annule et envoie des rappels."],
    ["Devis et prospects", "Collecte les bonnes informations et les enregistre dans le CRM."],
    ["Aucune invention", "Prix, services et horaires proviennent uniquement de vos données."],
    ["4 langues", "Détecte et répond en français, portugais, anglais et espagnol."],
    ["Un humain si nécessaire", "Reprenez n’importe quelle conversation depuis le tableau de bord."],
  ] },
  how: { title: "Prêt en quelques minutes", steps: ["Créez votre compte et choisissez votre activité", "Renseignez services, prix, horaires et FAQ", "Connectez votre site, WhatsApp ou Telegram"] },
  demo: { title: "Voyez l’agent en action", sub: "Discutez avec un agent de démonstration configuré pour un salon fictif.", illustrative: "Exemple illustratif de conversation (pas une conversation réelle).", open: "Ouvrir le chat de démonstration" },
  pricing: { title: "Des offres simples", month: "/mois", choose: "Choisir", note: "Prix en euros, TVA selon votre pays. Résiliable à tout moment.", plans: {
    FREE: ["Essai de 7 jours", "50 réponses IA", "Chat sur le site"],
    STARTER: ["500 réponses IA/mois", "1 agent personnalisé", "WhatsApp", "Tableau de bord de base"],
    PROFESSIONAL: ["2 000 réponses IA/mois", "WhatsApp et Telegram", "CRM complet", "Prise de rendez-vous automatique", "Rapports"],
    BUSINESS: ["5 000 réponses IA/mois", "Jusqu’à 20 utilisateurs", "Toutes les intégrations disponibles", "Support prioritaire"],
  } },
  faq: { title: "Questions fréquentes", items: [
    ["L’IA peut-elle inventer des prix ?", "Non. L’agent n’utilise que les données enregistrées. S’il ne sait pas, il propose un humain ou une demande de devis."],
    ["Faut-il des compétences techniques ?", "Non. Remplissez de simples formulaires. Pour le site, collez une ligne de code."],
    ["Comment fonctionne WhatsApp ?", "Nous utilisons l’API officielle WhatsApp Business Cloud de Meta. Un compte Meta Business vérifié et un numéro dédié sont nécessaires."],
    ["Et Telegram ?", "Créez un bot gratuit avec @BotFather et collez le jeton dans le tableau de bord."],
    ["Mes données sont-elles protégées ?", "Données isolées par entreprise, identifiants chiffrés, export et suppression à tout moment (RGPD)."],
    ["Que se passe-t-il à la limite du forfait ?", "L’agent envoie un message standard et transfère la conversation à un humain, sans frais supplémentaires."],
  ] },
  contact: { title: "Contactez l’équipe commerciale", sub: "Questions sur les offres, volumes ou intégrations ?", cta: "Envoyer un e-mail" },
  footer: { privacy: "Politique de confidentialité", terms: "Conditions d’utilisation" },
};

const en: Dict = {
  nav: { features: "Features", pricing: "Pricing", faq: "FAQ", login: "Log in", trial: "Free trial" },
  hero: { title: "An AI assistant for your business, 24 hours a day", sub: "Answers customers on WhatsApp, Telegram and your website, books appointments, records quote requests and hands over to you when needed — using only the information you approve.", cta: "Start 7-day free trial", note: "No credit card for the trial." },
  features: { title: "Everything you need to serve customers better", items: [
    ["24/7 support", "The agent replies even when you are offline."],
    ["Automatic booking", "Checks free slots, books, reschedules, cancels and sends reminders."],
    ["Quotes and leads", "Collects the right details and stores them in the CRM."],
    ["No made-up answers", "Prices, services and hours come only from your data."],
    ["4 languages", "Detects and replies in French, Portuguese, English and Spanish."],
    ["Human when needed", "Take over any conversation from the dashboard."],
  ] },
  how: { title: "Ready in minutes", steps: ["Create your account and pick your business type", "Add services, prices, hours and FAQs", "Connect your website, WhatsApp or Telegram"] },
  demo: { title: "See the agent in action", sub: "Chat with a demo agent set up for a fictional salon.", illustrative: "Illustrative example conversation (not a real conversation).", open: "Open demo chat" },
  pricing: { title: "Simple plans", month: "/month", choose: "Choose", note: "Prices in euros, VAT depending on your location. Cancel anytime.", plans: {
    FREE: ["7-day trial", "50 AI replies", "Website chat"],
    STARTER: ["500 AI replies/month", "1 custom agent", "WhatsApp", "Basic dashboard"],
    PROFESSIONAL: ["2,000 AI replies/month", "WhatsApp and Telegram", "Full CRM", "Automatic booking", "Reports"],
    BUSINESS: ["5,000 AI replies/month", "Up to 20 users", "All available integrations", "Priority support"],
  } },
  faq: { title: "Frequently asked questions", items: [
    ["Can the AI make up prices?", "No. The agent only uses the data you entered. If it doesn't know, it offers a human or a quote request."],
    ["Do I need technical skills?", "No. Fill in simple forms. For your website, paste one line of code."],
    ["How does WhatsApp work?", "We use Meta's official WhatsApp Business Cloud API. You need a verified Meta Business account and a dedicated number."],
    ["And Telegram?", "Create a free bot with @BotFather and paste the token in the dashboard."],
    ["Is my data safe?", "Isolated data per business, encrypted credentials, export or delete everything at any time (GDPR)."],
    ["What happens at the plan limit?", "The agent sends a standard message and hands the conversation to a human, at no extra cost."],
  ] },
  contact: { title: "Talk to sales", sub: "Questions about plans, volume or integrations?", cta: "Send an email" },
  footer: { privacy: "Privacy policy", terms: "Terms of use" },
};

const es: Dict = {
  nav: { features: "Funciones", pricing: "Planes", faq: "Preguntas", login: "Entrar", trial: "Prueba gratis" },
  hero: { title: "Un asistente de IA para su empresa, 24 horas al día", sub: "Responde a sus clientes en WhatsApp, Telegram y su web, agenda citas, registra presupuestos y le pasa la conversación cuando hace falta — solo con la información que usted autorice.", cta: "Empezar prueba gratis de 7 días", note: "Sin tarjeta durante la prueba." },
  features: { title: "Todo lo que su empresa necesita para atender mejor", items: [
    ["Atención 24/7", "El agente responde incluso cuando usted no está conectado."],
    ["Agenda automática", "Consulta huecos libres, reserva, cambia, cancela y envía recordatorios."],
    ["Presupuestos y clientes potenciales", "Recoge los datos adecuados y los guarda en el CRM."],
    ["Sin inventar nada", "Precios, servicios y horarios salen solo de sus datos."],
    ["4 idiomas", "Detecta y responde en francés, portugués, inglés y español."],
    ["Humano cuando haga falta", "Tome cualquier conversación desde el panel."],
  ] },
  how: { title: "Listo en pocos minutos", steps: ["Cree su cuenta y elija su tipo de negocio", "Indique servicios, precios, horarios y preguntas frecuentes", "Conecte su web, WhatsApp o Telegram"] },
  demo: { title: "Vea el agente en acción", sub: "Hable con un agente de demostración configurado para un salón ficticio.", illustrative: "Ejemplo ilustrativo de conversación (no es una conversación real).", open: "Abrir chat de demostración" },
  pricing: { title: "Planes sencillos", month: "/mes", choose: "Elegir", note: "Precios en euros, IVA según su ubicación. Cancele cuando quiera.", plans: {
    FREE: ["Prueba de 7 días", "50 respuestas de IA", "Chat en la web"],
    STARTER: ["500 respuestas de IA/mes", "1 agente personalizado", "WhatsApp", "Panel básico"],
    PROFESSIONAL: ["2.000 respuestas de IA/mes", "WhatsApp y Telegram", "CRM completo", "Agenda automática", "Informes"],
    BUSINESS: ["5.000 respuestas de IA/mes", "Hasta 20 usuarios", "Todas las integraciones disponibles", "Soporte prioritario"],
  } },
  faq: { title: "Preguntas frecuentes", items: [
    ["¿La IA puede inventar precios?", "No. El agente solo usa los datos registrados. Si no sabe, ofrece un humano o un presupuesto."],
    ["¿Necesito conocimientos técnicos?", "No. Rellene formularios sencillos. Para la web, pegue una línea de código."],
    ["¿Cómo funciona WhatsApp?", "Usamos la API oficial WhatsApp Business Cloud de Meta. Necesita una cuenta Meta Business verificada y un número dedicado."],
    ["¿Y Telegram?", "Cree un bot gratis con @BotFather y pegue el token en el panel."],
    ["¿Mis datos están seguros?", "Datos aislados por empresa, credenciales cifradas, exportación y borrado en cualquier momento (RGPD)."],
    ["¿Qué pasa al llegar al límite?", "El agente envía un mensaje estándar y pasa la conversación a un humano, sin coste extra."],
  ] },
  contact: { title: "Hable con el equipo comercial", sub: "¿Dudas sobre planes, volumen o integraciones?", cta: "Enviar correo" },
  footer: { privacy: "Política de privacidad", terms: "Términos de uso" },
};

export const DICTS: Record<Lang, Dict> = { pt, fr, en, es };

export function initialLang(): Lang {
  try { const s = localStorage.getItem("sb_lang") as Lang | null; if (s && DICTS[s]) return s; } catch { /* ignore */ }
  const n = (navigator.language || "pt").slice(0, 2) as Lang;
  return DICTS[n] ? n : "pt";
}
