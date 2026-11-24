import nodemailer from "nodemailer";
import { config } from "./config.js";

const transport = config.smtpUrl ? nodemailer.createTransport(config.smtpUrl) : null;
export const sentMails: { to: string; subject: string; text: string }[] = []; // usado nos testes

export async function sendMail(to: string, subject: string, text: string) {
  if (!transport) {
    if (config.isProd && config.emailVerification) throw new Error("SMTP_URL não configurado: e-mails de verificação não podem ser enviados");
    if (config.isProd) { console.warn(`[mail] SMTP_URL ausente — e-mail não enviado para ${to}: ${subject}`); return; }
    sentMails.push({ to, subject, text });
    console.log(`[mail:dev] para=${to} assunto=${subject}\n${text}`);
    return;
  }
  await transport.sendMail({ from: config.mailFrom, to, subject, text });
}
