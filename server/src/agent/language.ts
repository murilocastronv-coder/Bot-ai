/** Detecção leve de idioma (fr, pt, en, es) por palavras frequentes. */
const WORDS: Record<string, string[]> = {
  pt: ["olá", "ola", "obrigado", "obrigada", "você", "voce", "quero", "não", "nao", "por favor", "bom dia", "boa tarde", "quanto", "horário", "agendar", "tem", "preço", "é", "uma", "para", "com", "meu", "minha", "está"],
  fr: ["bonjour", "merci", "je", "vous", "voudrais", "est-ce", "pour", "avec", "rendez-vous", "combien", "prix", "oui", "non", "s'il", "c'est", "le", "la", "les", "une", "des", "quel", "quelle", "horaires"],
  en: ["hello", "hi", "thanks", "thank", "you", "want", "would", "like", "please", "the", "and", "how", "much", "price", "book", "appointment", "what", "is", "are", "can", "my", "i"],
  es: ["hola", "gracias", "quiero", "usted", "por favor", "buenos", "cuánto", "cuanto", "precio", "cita", "reservar", "el", "los", "las", "una", "para", "con", "mi", "está", "qué", "horario", "tienen"],
};
export function detectLanguage(text: string, allowed: string[] = ["pt", "fr", "en", "es"]): string | null {
  const t = ` ${text.toLowerCase().replace(/[!?.,;:¿¡()"]/g, " ")} `;
  let best: string | null = null, bestScore = 0;
  for (const [lang, words] of Object.entries(WORDS)) {
    if (!allowed.includes(lang)) continue;
    let s = 0;
    for (const w of words) if (t.includes(` ${w} `)) s += w.length > 3 ? 2 : 1;
    if (/[ãõç]/.test(t) && lang === "pt") s += 3;
    if (/[ñ¿¡]/.test(text) && lang === "es") s += 3;
    if (/[èêàùâœ]/.test(t) && lang === "fr") s += 3;
    if (s > bestScore) { bestScore = s; best = lang; }
  }
  return bestScore >= 2 ? best : null;
}
