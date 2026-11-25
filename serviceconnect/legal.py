"""Termos de Utilização e Política de Privacidade (RGPD) em 4 idiomas."""
from __future__ import annotations

from html import escape

from config import settings

UPDATED = "2026-11-25"

TERMS = {
    "pt": ("Termos de Utilização", [
        ("1. Serviço", "O ServiceConnect é uma plataforma no Telegram que coloca em contacto clientes e prestadores de serviços independentes. "
                       "Não somos parte dos contratos celebrados entre clientes e profissionais, não executamos os serviços e não garantimos o seu resultado."),
        ("2. Gratuidade", "No lançamento, a utilização é 100% gratuita, sem comissões nem mensalidades e sem pedido de cartão. Poderão ser criados planos "
                          "opcionais pagos no futuro; os usuários serão informados previamente e nenhuma cobrança será feita sem autorização expressa."),
        ("3. Conta", "Deve fornecer informações verdadeiras, ter pelo menos 16 anos e manter a sua conta segura. É proibido criar contas falsas, "
                     "manipular avaliações ou indicações."),
        ("4. Conduta", "É proibido publicar conteúdos ilegais, ofensivos, enganosos, spam, ou pedir pagamentos fora de acordos legítimos. "
                       "Os profissionais são responsáveis por possuir as licenças, seguros e obrigações fiscais exigidas pela sua atividade."),
        ("5. Avaliações", "Só é possível avaliar após um serviço registado como concluído. As avaliações devem ser honestas. Podemos ocultar conteúdos que violem estes termos."),
        ("6. Moderação", "Podemos suspender contas fraudulentas ou que violem estes termos. Pode denunciar perfis, pedidos e avaliações pelo bot."),
        ("7. Responsabilidade", "Na medida permitida por lei, o ServiceConnect não é responsável por danos resultantes de serviços contratados entre usuários."),
        ("8. Encerramento", "Pode excluir a sua conta a qualquer momento em «Meu perfil → Excluir conta»."),
        ("9. Alterações", "Podemos atualizar estes termos; alterações relevantes serão comunicadas pelo bot."),
    ]),
    "en": ("Terms of Use", [
        ("1. Service", "ServiceConnect is a Telegram platform connecting clients with independent service providers. We are not a party to agreements "
                       "between clients and professionals, we do not perform the services and we do not guarantee their outcome."),
        ("2. Free of charge", "At launch the service is 100% free: no commission, no subscription, no card required. Optional paid plans may be "
                              "introduced later; users will be informed in advance and nothing will be charged without explicit consent."),
        ("3. Account", "You must provide truthful information, be at least 16 and keep your account secure. Fake accounts and manipulation of reviews or referrals are forbidden."),
        ("4. Conduct", "Illegal, offensive or misleading content and spam are forbidden. Professionals are responsible for the licences, insurance and taxes their activity requires."),
        ("5. Reviews", "Reviews are only possible after a job is marked completed and must be honest. We may hide content breaching these terms."),
        ("6. Moderation", "We may suspend fraudulent accounts or accounts breaching these terms. You can report profiles, requests and reviews in the bot."),
        ("7. Liability", "To the extent permitted by law, ServiceConnect is not liable for damages arising from services contracted between users."),
        ("8. Termination", "You can delete your account at any time in «My profile → Delete account»."),
        ("9. Changes", "We may update these terms; significant changes will be announced in the bot."),
    ]),
    "fr": ("Conditions d'utilisation", [
        ("1. Service", "ServiceConnect est une plateforme Telegram qui met en relation des clients et des prestataires indépendants. Nous ne sommes pas "
                       "partie aux contrats conclus entre eux, n'exécutons pas les services et n'en garantissons pas le résultat."),
        ("2. Gratuité", "Au lancement, le service est 100 % gratuit : sans commission, sans abonnement, sans carte. Des formules payantes optionnelles "
                        "pourront être proposées ; les utilisateurs seront informés à l'avance et rien ne sera facturé sans accord explicite."),
        ("3. Compte", "Vous devez fournir des informations exactes, avoir au moins 16 ans et sécuriser votre compte. Les faux comptes et la manipulation des avis ou parrainages sont interdits."),
        ("4. Conduite", "Les contenus illégaux, offensants, trompeurs et le spam sont interdits. Les professionnels sont responsables de leurs licences, assurances et obligations fiscales."),
        ("5. Avis", "Un avis n'est possible qu'après une mission marquée comme terminée et doit être honnête. Nous pouvons masquer les contenus non conformes."),
        ("6. Modération", "Nous pouvons suspendre les comptes frauduleux. Vous pouvez signaler profils, demandes et avis dans le bot."),
        ("7. Responsabilité", "Dans les limites légales, ServiceConnect n'est pas responsable des dommages liés aux services conclus entre utilisateurs."),
        ("8. Résiliation", "Vous pouvez supprimer votre compte à tout moment : « Mon profil → Supprimer le compte »."),
        ("9. Modifications", "Nous pouvons modifier ces conditions ; les changements importants seront annoncés dans le bot."),
    ]),
    "es": ("Términos de uso", [
        ("1. Servicio", "ServiceConnect es una plataforma de Telegram que conecta clientes con profesionales independientes. No somos parte de los acuerdos "
                        "entre ellos, no prestamos los servicios ni garantizamos su resultado."),
        ("2. Gratuidad", "En el lanzamiento el uso es 100% gratuito: sin comisiones, sin cuotas y sin tarjeta. Podrán existir planes de pago opcionales; "
                         "se informará con antelación y nunca se cobrará nada sin autorización expresa."),
        ("3. Cuenta", "Debes dar información veraz, tener al menos 16 años y proteger tu cuenta. Prohibidas las cuentas falsas y la manipulación de valoraciones o invitaciones."),
        ("4. Conducta", "Prohibido el contenido ilegal, ofensivo, engañoso o spam. Los profesionales son responsables de sus licencias, seguros e impuestos."),
        ("5. Valoraciones", "Solo se puede valorar tras un trabajo marcado como completado y de forma honesta. Podemos ocultar contenido que infrinja estos términos."),
        ("6. Moderación", "Podemos suspender cuentas fraudulentas. Puedes denunciar perfiles, pedidos y valoraciones en el bot."),
        ("7. Responsabilidad", "En la medida permitida por la ley, ServiceConnect no responde de daños derivados de servicios contratados entre usuarios."),
        ("8. Baja", "Puedes eliminar tu cuenta en cualquier momento en «Mi perfil → Eliminar cuenta»."),
        ("9. Cambios", "Podemos actualizar estos términos; los cambios relevantes se anunciarán en el bot."),
    ]),
}

PRIVACY = {
    "pt": ("Política de Privacidade (RGPD)", [
        ("Responsável", "{company}. Contacto: pelo botão «🆘 Suporte» do bot{contact}."),
        ("Dados recolhidos", "Identificador e nome do Telegram, nome indicado, idioma, cidade e país, localização aproximada (só se a partilhar), "
                             "perfil profissional, fotos enviadas, pedidos, propostas, mensagens trocadas no bot, avaliações, denúncias e indicações."),
        ("Finalidades e bases legais", "Prestar o serviço de intermediação (execução de contrato, art. 6.º 1 b); segurança, prevenção de fraude e spam "
                                       "(interesse legítimo, art. 6.º 1 f); comunicados (pode desligá-los a qualquer momento no perfil)."),
        ("Partilha", "Outros usuários veem apenas o seu nome/nome profissional, cidade, perfil e avaliações. O seu número de telefone, @username e "
                     "localização exata nunca são mostrados. Não vendemos dados. Subcontratantes: Telegram (mensagens) e Render (alojamento, UE – Frankfurt)."),
        ("Conservação", "Enquanto a conta existir. Ao excluir a conta, os dados pessoais são apagados imediatamente; as cópias de segurança são substituídas em até 30 dias."),
        ("Os seus direitos", "Acesso e portabilidade («Meu perfil → Exportar meus dados»), retificação, apagamento («Excluir conta»), oposição e limitação. "
                             "Pode reclamar junto da autoridade de proteção de dados (ex.: CNPD em Portugal, CNIL em França)."),
        ("Segurança", "Dados guardados em PostgreSQL com acesso restrito, ligações cifradas, segredos em variáveis de ambiente e painel de administração protegido."),
    ]),
    "en": ("Privacy Policy (GDPR)", [
        ("Controller", "{company}. Contact: «🆘 Support» button in the bot{contact}."),
        ("Data collected", "Telegram ID and name, chosen name, language, city and country, approximate location (only if you share it), professional profile, "
                           "photos you send, requests, proposals, in-bot messages, reviews, reports and referrals."),
        ("Purposes and legal bases", "Providing the matching service (contract, Art. 6(1)(b)); security, fraud and spam prevention (legitimate interest, Art. 6(1)(f)); "
                                     "announcements (you can switch them off any time in your profile)."),
        ("Sharing", "Other users only see your (professional) name, city, profile and reviews. Your phone number, @username and exact location are never shown. "
                    "We never sell data. Processors: Telegram (messaging) and Render (hosting, EU – Frankfurt)."),
        ("Retention", "As long as your account exists. When you delete it, personal data is erased immediately; backups roll over within 30 days."),
        ("Your rights", "Access and portability («My profile → Export my data»), rectification, erasure («Delete account»), objection and restriction. "
                        "You may complain to your data protection authority."),
        ("Security", "Data stored in PostgreSQL with restricted access, encrypted connections, secrets in environment variables and a protected admin panel."),
    ]),
    "fr": ("Politique de confidentialité (RGPD)", [
        ("Responsable", "{company}. Contact : bouton « 🆘 Assistance » du bot{contact}."),
        ("Données collectées", "Identifiant et nom Telegram, nom choisi, langue, ville et pays, position approximative (seulement si vous la partagez), profil professionnel, "
                               "photos envoyées, demandes, propositions, messages échangés dans le bot, avis, signalements et parrainages."),
        ("Finalités et bases légales", "Fournir le service de mise en relation (contrat, art. 6.1.b) ; sécurité, prévention de la fraude et du spam (intérêt légitime, art. 6.1.f) ; "
                                       "annonces (désactivables à tout moment dans le profil)."),
        ("Partage", "Les autres utilisateurs voient seulement votre nom (professionnel), ville, profil et avis. Votre numéro, @username et position exacte ne sont jamais affichés. "
                    "Aucune vente de données. Sous-traitants : Telegram (messagerie) et Render (hébergement UE – Francfort)."),
        ("Conservation", "Tant que le compte existe. À la suppression, les données personnelles sont effacées immédiatement ; les sauvegardes sont renouvelées sous 30 jours."),
        ("Vos droits", "Accès et portabilité (« Mon profil → Exporter mes données »), rectification, effacement (« Supprimer le compte »), opposition et limitation. "
                       "Réclamation possible auprès de la CNIL ou de votre autorité."),
        ("Sécurité", "Données dans PostgreSQL à accès restreint, connexions chiffrées, secrets en variables d'environnement, panneau d'administration protégé."),
    ]),
    "es": ("Política de privacidad (RGPD)", [
        ("Responsable", "{company}. Contacto: botón «🆘 Soporte» del bot{contact}."),
        ("Datos recogidos", "ID y nombre de Telegram, nombre elegido, idioma, ciudad y país, ubicación aproximada (solo si la compartes), perfil profesional, "
                            "fotos enviadas, pedidos, propuestas, mensajes en el bot, valoraciones, denuncias e invitaciones."),
        ("Finalidades y bases legales", "Prestar el servicio de intermediación (contrato, art. 6.1.b); seguridad y prevención de fraude y spam (interés legítimo, art. 6.1.f); "
                                        "comunicados (puedes desactivarlos en tu perfil)."),
        ("Compartición", "Otros usuarios solo ven tu nombre (profesional), ciudad, perfil y valoraciones. Tu teléfono, @username y ubicación exacta nunca se muestran. "
                         "No vendemos datos. Encargados: Telegram (mensajería) y Render (alojamiento UE – Fráncfort)."),
        ("Conservación", "Mientras exista la cuenta. Al eliminarla, los datos personales se borran de inmediato; las copias de seguridad se renuevan en 30 días."),
        ("Tus derechos", "Acceso y portabilidad («Mi perfil → Exportar mis datos»), rectificación, supresión («Eliminar cuenta»), oposición y limitación. "
                         "Puedes reclamar ante la AEPD o tu autoridad."),
        ("Seguridad", "Datos en PostgreSQL con acceso restringido, conexiones cifradas, secretos en variables de entorno y panel de administración protegido."),
    ]),
}


def render_legal(kind: str, lang: str) -> str:
    lang = lang if lang in TERMS else "pt"
    title, sections = (TERMS if kind == "terms" else PRIVACY)[lang]
    contact = f" · {settings.support_contact}" if settings.support_contact else ""
    body = "".join(f"<h2>{escape(h)}</h2><p>{escape(p.format(company=settings.company_name, contact=contact))}</p>"
                   for h, p in sections)
    links = " · ".join(f'<a href="?lang={code}">{code.upper()}</a>' for code in TERMS)
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · ServiceConnect</title><style>
:root{{--bg:#fff;--ink:#1d2433;--muted:#6b7385}}@media (prefers-color-scheme:dark){{:root{{--bg:#0f131a;--ink:#e7eaf1;--muted:#9aa3b5}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
main{{max-width:760px;margin:auto;padding:24px 16px}}h1{{font-size:26px}}h2{{font-size:18px;margin-top:26px}}.muted{{color:var(--muted)}}a{{color:#2563eb}}
</style></head><body><main><p class="muted">{links}</p><h1>{escape(title)}</h1><p class="muted">ServiceConnect · {UPDATED}</p>{body}</main></body></html>"""
