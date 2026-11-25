"""Traduções: Português, Inglês, Francês e Espanhol."""
from __future__ import annotations

LANGS = ("pt", "en", "fr", "es")
LANG_NAMES = {"pt": "🇵🇹 Português", "en": "🇬🇧 English", "fr": "🇫🇷 Français", "es": "🇪🇸 Español"}

# chave: (pt, en, fr, es)
_T: dict[str, tuple[str, str, str, str]] = {
    # ---------- menu principal ----------
    "menu.find": ("🔎 Encontrar profissional", "🔎 Find a professional", "🔎 Trouver un professionnel", "🔎 Encontrar profesional"),
    "menu.publish": ("📢 Publicar um serviço", "📢 Post a job", "📢 Publier une demande", "📢 Publicar un servicio"),
    "menu.jobs": ("💼 Encontrar trabalho", "💼 Find work", "💼 Trouver du travail", "💼 Encontrar trabajo"),
    "menu.profile": ("👤 Meu perfil", "👤 My profile", "👤 Mon profil", "👤 Mi perfil"),
    "menu.requests": ("📋 Minhas solicitações", "📋 My requests", "📋 Mes demandes", "📋 Mis solicitudes"),
    "menu.messages": ("💬 Minhas mensagens", "💬 My messages", "💬 Mes messages", "💬 Mis mensajes"),
    "menu.reviews": ("⭐ Avaliações", "⭐ Reviews", "⭐ Avis", "⭐ Valoraciones"),
    "menu.location": ("📍 Alterar localização", "📍 Change location", "📍 Changer de lieu", "📍 Cambiar ubicación"),
    "menu.invite": ("👥 Convidar amigos", "👥 Invite friends", "👥 Inviter des amis", "👥 Invitar amigos"),
    "menu.language": ("🌐 Idioma", "🌐 Language", "🌐 Langue", "🌐 Idioma"),
    "menu.support": ("🆘 Suporte", "🆘 Support", "🆘 Assistance", "🆘 Soporte"),
    "menu.title": ("🏠 <b>Menu principal</b>\nEscolha uma opção abaixo 👇", "🏠 <b>Main menu</b>\nChoose an option below 👇",
                   "🏠 <b>Menu principal</b>\nChoisissez une option ci-dessous 👇", "🏠 <b>Menú principal</b>\nElige una opción abajo 👇"),
    # ---------- comuns ----------
    "btn.back": ("⬅️ Voltar", "⬅️ Back", "⬅️ Retour", "⬅️ Volver"),
    "btn.cancel": ("✖️ Cancelar", "✖️ Cancel", "✖️ Annuler", "✖️ Cancelar"),
    "btn.skip": ("⏭ Pular", "⏭ Skip", "⏭ Passer", "⏭ Omitir"),
    "btn.done": ("✅ Concluir", "✅ Done", "✅ Terminer", "✅ Listo"),
    "btn.confirm": ("✅ Confirmar", "✅ Confirm", "✅ Confirmer", "✅ Confirmar"),
    "btn.yes": ("Sim", "Yes", "Oui", "Sí"),
    "btn.no": ("Não", "No", "Non", "No"),
    "btn.more": ("➡️ Mais", "➡️ More", "➡️ Plus", "➡️ Más"),
    "cancelled": ("Operação cancelada.", "Cancelled.", "Opération annulée.", "Operación cancelada."),
    "not_found": ("Não encontrado ou já não está disponível.", "Not found or no longer available.",
                  "Introuvable ou plus disponible.", "No encontrado o ya no disponible."),
    "not_allowed": ("Você não tem permissão para isso.", "You are not allowed to do this.",
                    "Vous n'avez pas l'autorisation.", "No tienes permiso para esto."),
    "banned": ("🚫 Sua conta está suspensa. Contacte o suporte se achar que é um erro.",
               "🚫 Your account is suspended. Contact support if you think this is a mistake.",
               "🚫 Votre compte est suspendu. Contactez l'assistance s'il s'agit d'une erreur.",
               "🚫 Tu cuenta está suspendida. Contacta con soporte si crees que es un error."),
    "slow_down": ("⏳ Muitas ações seguidas. Aguarde um instante.", "⏳ Too many actions. Please wait a moment.",
                  "⏳ Trop d'actions. Patientez un instant.", "⏳ Demasiadas acciones. Espera un momento."),
    "daily_limit": ("Você atingiu o limite diário. Tente amanhã.", "Daily limit reached. Try again tomorrow.",
                    "Limite quotidienne atteinte. Réessayez demain.", "Has alcanzado el límite diario. Inténtalo mañana."),
    "error": ("⚠️ Ocorreu um erro. Tente novamente.", "⚠️ Something went wrong. Please try again.",
              "⚠️ Une erreur s'est produite. Réessayez.", "⚠️ Ocurrió un error. Inténtalo de nuevo."),
    "too_long": ("Texto muito longo (máx. {n} caracteres).", "Text too long (max {n} characters).",
                 "Texte trop long (max {n} caractères).", "Texto demasiado largo (máx. {n} caracteres)."),
    "send_text": ("Envie um texto, por favor.", "Please send text.", "Envoyez un texte, svp.", "Envía un texto, por favor."),
    # ---------- onboarding ----------
    "welcome": ("👋 Bem-vindo(a) ao <b>ServiceConnect</b>!\n\nO marketplace que conecta clientes e profissionais perto de você.\n"
                "✅ 100% gratuito · sem comissões · sem cartão\n\nAntes de começar, leia e aceite os "
                "<a href=\"{terms}\">Termos de Utilização</a> e a <a href=\"{privacy}\">Política de Privacidade</a>.",
                "👋 Welcome to <b>ServiceConnect</b>!\n\nThe marketplace connecting clients and professionals near you.\n"
                "✅ 100% free · no commission · no card\n\nBefore starting, please read and accept the "
                "<a href=\"{terms}\">Terms of Use</a> and the <a href=\"{privacy}\">Privacy Policy</a>.",
                "👋 Bienvenue sur <b>ServiceConnect</b> !\n\nLa place de marché qui relie clients et professionnels près de chez vous.\n"
                "✅ 100 % gratuit · sans commission · sans carte\n\nAvant de commencer, lisez et acceptez les "
                "<a href=\"{terms}\">Conditions d'utilisation</a> et la <a href=\"{privacy}\">Politique de confidentialité</a>.",
                "👋 ¡Bienvenido(a) a <b>ServiceConnect</b>!\n\nEl marketplace que conecta clientes y profesionales cerca de ti.\n"
                "✅ 100% gratis · sin comisiones · sin tarjeta\n\nAntes de empezar, lee y acepta los "
                "<a href=\"{terms}\">Términos de uso</a> y la <a href=\"{privacy}\">Política de privacidad</a>."),
    "btn.accept_terms": ("✅ Li e aceito", "✅ I read and accept", "✅ J'ai lu et j'accepte", "✅ He leído y acepto"),
    "ask_name": ("Como devemos chamar você? Envie seu nome ou use o botão.", "What should we call you? Send your name or use the button.",
                 "Comment devons-nous vous appeler ? Envoyez votre nom ou utilisez le bouton.", "¿Cómo te llamamos? Envía tu nombre o usa el botón."),
    "ask_role": ("Como você vai usar o ServiceConnect?", "How will you use ServiceConnect?",
                 "Comment allez-vous utiliser ServiceConnect ?", "¿Cómo usarás ServiceConnect?"),
    "btn.role_client": ("🙋 Sou cliente (procuro serviços)", "🙋 I'm a client (looking for services)",
                        "🙋 Je suis client (je cherche des services)", "🙋 Soy cliente (busco servicios)"),
    "btn.role_provider": ("🧰 Sou profissional (ofereço serviços)", "🧰 I'm a professional (I offer services)",
                          "🧰 Je suis professionnel (j'offre des services)", "🧰 Soy profesional (ofrezco servicios)"),
    "ask_location": ("📍 Em que cidade você está?\n\nEnvie o nome da cidade (ex.: <i>Lisboa, PT</i>) ou toque em «Partilhar localização» "
                     "para resultados mais precisos. A sua localização exata nunca é mostrada a outros usuários.",
                     "📍 Which city are you in?\n\nSend the city name (e.g. <i>London, GB</i>) or tap «Share location» for more accurate "
                     "results. Your exact location is never shown to other users.",
                     "📍 Dans quelle ville êtes-vous ?\n\nEnvoyez le nom de la ville (ex. : <i>Paris, FR</i>) ou touchez « Partager la position » "
                     "pour des résultats plus précis. Votre position exacte n'est jamais montrée aux autres.",
                     "📍 ¿En qué ciudad estás?\n\nEnvía el nombre de la ciudad (ej.: <i>Madrid, ES</i>) o toca «Compartir ubicación» "
                     "para resultados más precisos. Tu ubicación exacta nunca se muestra a otros usuarios."),
    "btn.share_location": ("📍 Partilhar localização", "📍 Share location", "📍 Partager la position", "📍 Compartir ubicación"),
    "location_saved": ("✅ Localização atualizada: <b>{city}</b>", "✅ Location updated: <b>{city}</b>",
                       "✅ Position mise à jour : <b>{city}</b>", "✅ Ubicación actualizada: <b>{city}</b>"),
    "location_city_unknown": ("✅ Coordenadas guardadas. Agora envie o nome da sua cidade (ex.: <i>Porto, PT</i>).",
                              "✅ Coordinates saved. Now send your city name (e.g. <i>Paris, FR</i>).",
                              "✅ Coordonnées enregistrées. Envoyez maintenant le nom de votre ville (ex. : <i>Lyon, FR</i>).",
                              "✅ Coordenadas guardadas. Ahora envía el nombre de tu ciudad (ej.: <i>Sevilla, ES</i>)."),
    "onboard_done": ("🎉 Tudo pronto, {name}! Use o menu abaixo.", "🎉 All set, {name}! Use the menu below.",
                     "🎉 C'est prêt, {name} ! Utilisez le menu ci-dessous.", "🎉 ¡Todo listo, {name}! Usa el menú de abajo."),
    "need_onboarding": ("Primeiro conclua o cadastro: /start", "Please finish sign-up first: /start",
                        "Terminez d'abord l'inscription : /start", "Primero completa el registro: /start"),
    # ---------- categorias / pesquisa ----------
    "choose_category": ("Escolha a categoria:", "Choose a category:", "Choisissez une catégorie :", "Elige la categoría:"),
    "choose_radius": ("Distância máxima de busca:", "Maximum search distance:", "Distance maximale :", "Distancia máxima de búsqueda:"),
    "radius_city": ("🏙 Só na minha cidade", "🏙 My city only", "🏙 Ma ville uniquement", "🏙 Solo mi ciudad"),
    "no_providers": ("😕 Ainda não há profissionais nesta categoria perto de você.\n\nPublique um pedido em «📢 Publicar um serviço» — "
                     "avisaremos os profissionais que se cadastrarem!",
                     "😕 No professionals in this category near you yet.\n\nPost a job with «📢 Post a job» — we'll notify professionals as they join!",
                     "😕 Pas encore de professionnels dans cette catégorie près de vous.\n\nPubliez une demande avec « 📢 Publier une demande » — "
                     "nous préviendrons les professionnels inscrits !",
                     "😕 Aún no hay profesionales en esta categoría cerca de ti.\n\nPublica un pedido en «📢 Publicar un servicio» — "
                     "¡avisaremos a los profesionales que se registren!"),
    "providers_found": ("🔎 <b>{n}</b> profissional(is) encontrado(s):", "🔎 <b>{n}</b> professional(s) found:",
                        "🔎 <b>{n}</b> professionnel(s) trouvé(s) :", "🔎 <b>{n}</b> profesional(es) encontrado(s):"),
    "verified": ("✅ Verificado", "✅ Verified", "✅ Vérifié", "✅ Verificado"),
    "sponsored": ("⭐ Destaque", "⭐ Featured", "⭐ En vedette", "⭐ Destacado"),
    "no_reviews_yet": ("sem avaliações", "no reviews", "aucun avis", "sin valoraciones"),
    "price_hourly": ("{rate} {cur}/hora", "{rate} {cur}/hour", "{rate} {cur}/heure", "{rate} {cur}/hora"),
    "price_quote": ("Orçamento personalizado", "Custom quote", "Devis personnalisé", "Presupuesto personalizado"),
    "km_away": ("a {km} km", "{km} km away", "à {km} km", "a {km} km"),
    "provider_card": ("<b>{name}</b> {badges}\n⭐ {rating} · 🛠 {jobs} trabalho(s)\n📍 {city} · raio {radius} km\n💶 {price}\n🗓 {availability}\n\n{description}\n\n🏷 {cats}",
                      "<b>{name}</b> {badges}\n⭐ {rating} · 🛠 {jobs} job(s)\n📍 {city} · radius {radius} km\n💶 {price}\n🗓 {availability}\n\n{description}\n\n🏷 {cats}",
                      "<b>{name}</b> {badges}\n⭐ {rating} · 🛠 {jobs} mission(s)\n📍 {city} · rayon {radius} km\n💶 {price}\n🗓 {availability}\n\n{description}\n\n🏷 {cats}",
                      "<b>{name}</b> {badges}\n⭐ {rating} · 🛠 {jobs} trabajo(s)\n📍 {city} · radio {radius} km\n💶 {price}\n🗓 {availability}\n\n{description}\n\n🏷 {cats}"),
    "btn.contact": ("💬 Enviar mensagem", "💬 Send message", "💬 Envoyer un message", "💬 Enviar mensaje"),
    "btn.portfolio": ("🖼 Portfólio", "🖼 Portfolio", "🖼 Portfolio", "🖼 Portafolio"),
    "btn.see_reviews": ("⭐ Ver avaliações", "⭐ See reviews", "⭐ Voir les avis", "⭐ Ver valoraciones"),
    "btn.report": ("🚩 Denunciar", "🚩 Report", "🚩 Signaler", "🚩 Denunciar"),
    "btn.share": ("📤 Partilhar", "📤 Share", "📤 Partager", "📤 Compartir"),
    "portfolio_empty": ("Este profissional ainda não adicionou fotos.", "No portfolio photos yet.",
                        "Aucune photo dans le portfolio.", "Aún no hay fotos en el portafolio."),
    # ---------- publicar pedido ----------
    "req.ask_description": ("📝 Descreva o trabalho (o que precisa, tamanho, materiais…):", "📝 Describe the job (what you need, size, materials…):",
                            "📝 Décrivez le travail (besoin, taille, matériaux…) :", "📝 Describe el trabajo (qué necesitas, tamaño, materiales…):"),
    "req.ask_photos": ("📷 Envie até 5 fotos (opcional). Quando terminar, toque em «Concluir».",
                       "📷 Send up to 5 photos (optional). Tap «Done» when finished.",
                       "📷 Envoyez jusqu'à 5 photos (facultatif). Touchez « Terminer » quand c'est fini.",
                       "📷 Envía hasta 5 fotos (opcional). Toca «Listo» al terminar."),
    "req.photo_added": ("📷 Foto {n}/5 adicionada.", "📷 Photo {n}/5 added.", "📷 Photo {n}/5 ajoutée.", "📷 Foto {n}/5 añadida."),
    "req.ask_city": ("🏙 Em que cidade será o serviço? Envie o nome ou use o botão.", "🏙 Which city is the job in? Send the name or use the button.",
                     "🏙 Dans quelle ville ? Envoyez le nom ou utilisez le bouton.", "🏙 ¿En qué ciudad será el servicio? Envía el nombre o usa el botón."),
    "req.ask_budget": ("💶 Qual é o orçamento disponível? (ex.: 100 €)", "💶 What's your budget? (e.g. €100)",
                       "💶 Quel est votre budget ? (ex. : 100 €)", "💶 ¿Cuál es tu presupuesto? (ej.: 100 €)"),
    "req.ask_date": ("📅 Para quando? (ex.: 12/12, esta semana, flexível)", "📅 When? (e.g. 12/12, this week, flexible)",
                     "📅 Pour quand ? (ex. : 12/12, cette semaine, flexible)", "📅 ¿Para cuándo? (ej.: 12/12, esta semana, flexible)"),
    "req.ask_urgency": ("⏱ Nível de urgência:", "⏱ Urgency level:", "⏱ Niveau d'urgence :", "⏱ Nivel de urgencia:"),
    "urg.low": ("🟢 Sem pressa", "🟢 No rush", "🟢 Pas pressé", "🟢 Sin prisa"),
    "urg.normal": ("🟡 Normal", "🟡 Normal", "🟡 Normal", "🟡 Normal"),
    "urg.high": ("🟠 Alta", "🟠 High", "🟠 Élevée", "🟠 Alta"),
    "urg.urgent": ("🔴 Urgente", "🔴 Urgent", "🔴 Urgent", "🔴 Urgente"),
    "req.summary": ("<b>Confirme o seu pedido</b>\n\n🏷 {cat}\n📝 {desc}\n📷 {photos} foto(s)\n🏙 {city}\n💶 {budget}\n📅 {date}\n⏱ {urgency}",
                    "<b>Confirm your request</b>\n\n🏷 {cat}\n📝 {desc}\n📷 {photos} photo(s)\n🏙 {city}\n💶 {budget}\n📅 {date}\n⏱ {urgency}",
                    "<b>Confirmez votre demande</b>\n\n🏷 {cat}\n📝 {desc}\n📷 {photos} photo(s)\n🏙 {city}\n💶 {budget}\n📅 {date}\n⏱ {urgency}",
                    "<b>Confirma tu pedido</b>\n\n🏷 {cat}\n📝 {desc}\n📷 {photos} foto(s)\n🏙 {city}\n💶 {budget}\n📅 {date}\n⏱ {urgency}"),
    "req.published": ("✅ Pedido #{id} publicado! Notificamos <b>{n}</b> profissional(is) compatível(is). Você receberá as propostas aqui.",
                      "✅ Request #{id} posted! We notified <b>{n}</b> matching professional(s). You'll receive proposals here.",
                      "✅ Demande #{id} publiée ! <b>{n}</b> professionnel(s) compatible(s) prévenu(s). Vous recevrez les propositions ici.",
                      "✅ ¡Pedido #{id} publicado! Avisamos a <b>{n}</b> profesional(es) compatible(s). Recibirás las propuestas aquí."),
    "btn.share_request": ("📤 Partilhar em grupos", "📤 Share in groups", "📤 Partager dans des groupes", "📤 Compartir en grupos"),
    "not_specified": ("não indicado", "not specified", "non précisé", "no indicado"),
    "req.card": ("📢 <b>Pedido #{id}</b> · {cat}\n📝 {desc}\n🏙 {city} {dist}\n💶 {budget} · 📅 {date}\n⏱ {urgency} · 📨 {proposals} proposta(s)\n🕒 {created}",
                 "📢 <b>Request #{id}</b> · {cat}\n📝 {desc}\n🏙 {city} {dist}\n💶 {budget} · 📅 {date}\n⏱ {urgency} · 📨 {proposals} proposal(s)\n🕒 {created}",
                 "📢 <b>Demande #{id}</b> · {cat}\n📝 {desc}\n🏙 {city} {dist}\n💶 {budget} · 📅 {date}\n⏱ {urgency} · 📨 {proposals} proposition(s)\n🕒 {created}",
                 "📢 <b>Pedido #{id}</b> · {cat}\n📝 {desc}\n🏙 {city} {dist}\n💶 {budget} · 📅 {date}\n⏱ {urgency} · 📨 {proposals} propuesta(s)\n🕒 {created}"),
    "new_request_notify": ("🔔 <b>Novo pedido perto de você!</b>", "🔔 <b>New job near you!</b>",
                           "🔔 <b>Nouvelle demande près de chez vous !</b>", "🔔 <b>¡Nuevo pedido cerca de ti!</b>"),
    "status.open": ("🟢 Aberto", "🟢 Open", "🟢 Ouverte", "🟢 Abierto"),
    "status.assigned": ("🤝 Contratado", "🤝 Hired", "🤝 Attribuée", "🤝 Contratado"),
    "status.completed": ("✅ Concluído", "✅ Completed", "✅ Terminée", "✅ Completado"),
    "status.cancelled": ("❌ Cancelado", "❌ Cancelled", "❌ Annulée", "❌ Cancelado"),
    "status.hidden": ("🚫 Removido", "🚫 Removed", "🚫 Retirée", "🚫 Eliminado"),
    # ---------- trabalho / propostas ----------
    "become_provider_first": ("Para encontrar trabalho, crie primeiro o seu perfil profissional (gratuito).",
                              "To find work, create your professional profile first (free).",
                              "Pour trouver du travail, créez d'abord votre profil professionnel (gratuit).",
                              "Para encontrar trabajo, crea primero tu perfil profesional (gratis)."),
    "btn.become_provider": ("🧰 Criar perfil profissional", "🧰 Create professional profile", "🧰 Créer un profil pro", "🧰 Crear perfil profesional"),
    "no_jobs": ("Nenhum pedido aberto compatível com as suas especialidades e área agora. Avisaremos quando surgir um! 🔔",
                "No open jobs match your specialties and area right now. We'll notify you! 🔔",
                "Aucune demande ouverte ne correspond pour l'instant. Nous vous préviendrons ! 🔔",
                "No hay pedidos abiertos compatibles ahora. ¡Te avisaremos! 🔔"),
    "jobs_found": ("💼 <b>{n}</b> pedido(s) disponível(is):", "💼 <b>{n}</b> job(s) available:",
                   "💼 <b>{n}</b> demande(s) disponible(s) :", "💼 <b>{n}</b> pedido(s) disponible(s):"),
    "btn.send_proposal": ("📝 Enviar orçamento", "📝 Send quote", "📝 Envoyer un devis", "📝 Enviar presupuesto"),
    "btn.message_client": ("💬 Perguntar ao cliente", "💬 Ask the client", "💬 Poser une question", "💬 Preguntar al cliente"),
    "prop.ask_price": ("💶 Qual é o seu preço para este trabalho? (ex.: 120 €, 25 €/h)", "💶 Your price for this job? (e.g. €120, €25/h)",
                       "💶 Votre prix pour ce travail ? (ex. : 120 €, 25 €/h)", "💶 ¿Tu precio para este trabajo? (ej.: 120 €, 25 €/h)"),
    "prop.ask_availability": ("🗓 Quando você está disponível? (ex.: sábado de manhã)", "🗓 When are you available? (e.g. Saturday morning)",
                              "🗓 Quand êtes-vous disponible ? (ex. : samedi matin)", "🗓 ¿Cuándo estás disponible? (ej.: sábado por la mañana)"),
    "prop.ask_message": ("✍️ Mensagem para o cliente (apresente-se, explique o que inclui):", "✍️ Message to the client (introduce yourself, what's included):",
                         "✍️ Message au client (présentez-vous, ce qui est inclus) :", "✍️ Mensaje para el cliente (preséntate, qué incluye):"),
    "prop.sent": ("✅ Proposta enviada! Você será avisado quando o cliente responder.", "✅ Proposal sent! You'll be notified when the client responds.",
                  "✅ Proposition envoyée ! Vous serez prévenu de la réponse du client.", "✅ ¡Propuesta enviada! Te avisaremos cuando el cliente responda."),
    "prop.already": ("Você já enviou uma proposta para este pedido.", "You already sent a proposal for this request.",
                     "Vous avez déjà envoyé une proposition.", "Ya enviaste una propuesta para este pedido."),
    "prop.own_request": ("Não pode enviar proposta para o seu próprio pedido.", "You can't bid on your own request.",
                         "Impossible de répondre à votre propre demande.", "No puedes ofertar en tu propio pedido."),
    "prop.new_notify": ("📨 <b>Nova proposta</b> para o pedido #{id}!\n\n{card}", "📨 <b>New proposal</b> for request #{id}!\n\n{card}",
                        "📨 <b>Nouvelle proposition</b> pour la demande #{id} !\n\n{card}", "📨 <b>¡Nueva propuesta</b> para el pedido #{id}!\n\n{card}"),
    "prop.card": ("👤 <b>{name}</b> {badges}\n⭐ {rating} · 🛠 {jobs}\n💶 <b>{price}</b>\n🗓 {availability}\n💬 {message}",
                  "👤 <b>{name}</b> {badges}\n⭐ {rating} · 🛠 {jobs}\n💶 <b>{price}</b>\n🗓 {availability}\n💬 {message}",
                  "👤 <b>{name}</b> {badges}\n⭐ {rating} · 🛠 {jobs}\n💶 <b>{price}</b>\n🗓 {availability}\n💬 {message}",
                  "👤 <b>{name}</b> {badges}\n⭐ {rating} · 🛠 {jobs}\n💶 <b>{price}</b>\n🗓 {availability}\n💬 {message}"),
    "btn.view_proposals": ("📨 Ver propostas ({n})", "📨 View proposals ({n})", "📨 Voir les propositions ({n})", "📨 Ver propuestas ({n})"),
    "btn.hire": ("🤝 Contratar", "🤝 Hire", "🤝 Engager", "🤝 Contratar"),
    "btn.chat": ("💬 Conversar", "💬 Chat", "💬 Discuter", "💬 Chatear"),
    "btn.profile": ("👤 Perfil", "👤 Profile", "👤 Profil", "👤 Perfil"),
    "no_proposals": ("Ainda não há propostas. Avisaremos assim que chegar uma! 🔔", "No proposals yet. We'll let you know! 🔔",
                     "Pas encore de propositions. Nous vous préviendrons ! 🔔", "Aún no hay propuestas. ¡Te avisaremos! 🔔"),
    "proposals_compare": ("📊 <b>Propostas para o pedido #{id}</b> (ordenadas por avaliação e preço):",
                          "📊 <b>Proposals for request #{id}</b> (sorted by rating and price):",
                          "📊 <b>Propositions pour la demande #{id}</b> (triées par note et prix) :",
                          "📊 <b>Propuestas para el pedido #{id}</b> (ordenadas por valoración y precio):"),
    "hired_client": ("🤝 Você contratou <b>{name}</b>! Aguardando a confirmação do profissional. Combine os detalhes pelo chat.",
                     "🤝 You hired <b>{name}</b>! Waiting for the professional to confirm. Arrange details via chat.",
                     "🤝 Vous avez engagé <b>{name}</b> ! En attente de confirmation. Organisez les détails par le chat.",
                     "🤝 ¡Has contratado a <b>{name}</b>! Esperando la confirmación del profesional. Acordad los detalles por el chat."),
    "hired_provider": ("🎉 <b>Você foi contratado(a)</b> para o pedido #{id}!\n\n{card}\n\nAceita este trabalho?",
                       "🎉 <b>You were hired</b> for request #{id}!\n\n{card}\n\nDo you accept this job?",
                       "🎉 <b>Vous avez été engagé(e)</b> pour la demande #{id} !\n\n{card}\n\nAcceptez-vous ce travail ?",
                       "🎉 <b>¡Te han contratado</b> para el pedido #{id}!\n\n{card}\n\n¿Aceptas este trabajo?"),
    "btn.accept_job": ("✅ Aceitar trabalho", "✅ Accept job", "✅ Accepter", "✅ Aceptar trabajo"),
    "btn.decline_job": ("❌ Recusar", "❌ Decline", "❌ Refuser", "❌ Rechazar"),
    "job_accepted_provider": ("✅ Trabalho confirmado. Bom serviço!", "✅ Job confirmed. Good luck!", "✅ Travail confirmé. Bon travail !", "✅ Trabajo confirmado. ¡Buen trabajo!"),
    "job_accepted_client": ("✅ <b>{name}</b> confirmou o trabalho do pedido #{id}. Quando terminar, marque como concluído em «📋 Minhas solicitações».",
                            "✅ <b>{name}</b> confirmed the job for request #{id}. When done, mark it completed in «📋 My requests».",
                            "✅ <b>{name}</b> a confirmé la demande #{id}. Une fois terminé, marquez-la comme terminée dans « 📋 Mes demandes ».",
                            "✅ <b>{name}</b> confirmó el pedido #{id}. Al terminar, márcalo como completado en «📋 Mis solicitudes»."),
    "job_declined_client": ("😕 O profissional recusou o pedido #{id}. O pedido voltou a ficar aberto para outras propostas.",
                            "😕 The professional declined request #{id}. It's open again for other proposals.",
                            "😕 Le professionnel a refusé la demande #{id}. Elle est de nouveau ouverte.",
                            "😕 El profesional rechazó el pedido #{id}. Vuelve a estar abierto."),
    "job_declined_provider": ("Trabalho recusado.", "Job declined.", "Travail refusé.", "Trabajo rechazado."),
    "proposal_rejected": ("O cliente escolheu outra proposta para o pedido #{id}. Continue a enviar orçamentos! 💪",
                          "The client chose another proposal for request #{id}. Keep sending quotes! 💪",
                          "Le client a choisi une autre proposition pour la demande #{id}. Continuez ! 💪",
                          "El cliente eligió otra propuesta para el pedido #{id}. ¡Sigue enviando presupuestos! 💪"),
    # ---------- minhas solicitações ----------
    "my_requests_empty": ("Você ainda não publicou pedidos.", "You haven't posted any requests yet.",
                          "Vous n'avez encore publié aucune demande.", "Aún no has publicado pedidos."),
    "my_requests": ("📋 <b>Suas solicitações</b>:", "📋 <b>Your requests</b>:", "📋 <b>Vos demandes</b> :", "📋 <b>Tus solicitudes</b>:"),
    "my_jobs": ("🧰 <b>Seus trabalhos como profissional</b>:", "🧰 <b>Your jobs as a professional</b>:",
                "🧰 <b>Vos missions de professionnel</b> :", "🧰 <b>Tus trabajos como profesional</b>:"),
    "btn.complete": ("✅ Marcar como concluído", "✅ Mark as completed", "✅ Marquer comme terminé", "✅ Marcar como completado"),
    "btn.cancel_request": ("❌ Cancelar pedido", "❌ Cancel request", "❌ Annuler la demande", "❌ Cancelar pedido"),
    "request_cancelled": ("Pedido cancelado.", "Request cancelled.", "Demande annulée.", "Pedido cancelado."),
    "request_completed": ("✅ Pedido marcado como concluído. Avalie o profissional:", "✅ Marked as completed. Rate the professional:",
                          "✅ Marquée comme terminée. Évaluez le professionnel :", "✅ Marcado como completado. Valora al profesional:"),
    "provider_job_completed": ("✅ O cliente marcou o pedido #{id} como concluído. Parabéns!", "✅ The client marked request #{id} as completed. Well done!",
                               "✅ Le client a marqué la demande #{id} comme terminée. Bravo !", "✅ El cliente marcó el pedido #{id} como completado. ¡Enhorabuena!"),
    # ---------- mensagens ----------
    "no_conversations": ("Nenhuma conversa ainda.", "No conversations yet.", "Aucune conversation.", "Aún no hay conversaciones."),
    "conversations": ("💬 <b>Suas conversas</b>:", "💬 <b>Your conversations</b>:", "💬 <b>Vos conversations</b> :", "💬 <b>Tus conversaciones</b>:"),
    "chat_open": ("💬 Conversa com <b>{name}</b>{req}\nEscreva a sua mensagem ou envie uma foto. O seu número de telefone não é partilhado.\n\n{history}",
                  "💬 Chat with <b>{name}</b>{req}\nType your message or send a photo. Your phone number is never shared.\n\n{history}",
                  "💬 Conversation avec <b>{name}</b>{req}\nÉcrivez votre message ou envoyez une photo. Votre numéro n'est jamais partagé.\n\n{history}",
                  "💬 Chat con <b>{name}</b>{req}\nEscribe tu mensaje o envía una foto. Tu número nunca se comparte.\n\n{history}"),
    "btn.exit_chat": ("🚪 Sair da conversa", "🚪 Leave chat", "🚪 Quitter la conversation", "🚪 Salir del chat"),
    "btn.reply": ("↩️ Responder", "↩️ Reply", "↩️ Répondre", "↩️ Responder"),
    "msg_sent": ("✓ Enviada", "✓ Sent", "✓ Envoyé", "✓ Enviado"),
    "msg_incoming": ("💬 <b>{name}</b>{req}:\n{text}", "💬 <b>{name}</b>{req}:\n{text}", "💬 <b>{name}</b>{req} :\n{text}", "💬 <b>{name}</b>{req}:\n{text}"),
    "chat_closed": ("Você saiu da conversa.", "You left the chat.", "Vous avez quitté la conversation.", "Saliste del chat."),
    "you": ("Você", "You", "Vous", "Tú"),
    "photo": ("📷 foto", "📷 photo", "📷 photo", "📷 foto"),
    "cant_message_self": ("Não pode enviar mensagens para si mesmo.", "You can't message yourself.", "Impossible de vous écrire à vous-même.", "No puedes escribirte a ti mismo."),
    # ---------- avaliações ----------
    "reviews_title": ("⭐ <b>Avaliações</b>", "⭐ <b>Reviews</b>", "⭐ <b>Avis</b>", "⭐ <b>Valoraciones</b>"),
    "reviews_pending": ("Serviços concluídos à espera da sua avaliação:", "Completed jobs waiting for your review:",
                        "Missions terminées en attente de votre avis :", "Trabajos completados esperando tu valoración:"),
    "reviews_received": ("Avaliações recebidas ({avg} ⭐, {n}):", "Reviews received ({avg} ⭐, {n}):", "Avis reçus ({avg} ⭐, {n}) :", "Valoraciones recibidas ({avg} ⭐, {n}):"),
    "reviews_none": ("Ainda não há avaliações.", "No reviews yet.", "Pas encore d'avis.", "Aún no hay valoraciones."),
    "btn.rate": ("⭐ Avaliar #{id}", "⭐ Rate #{id}", "⭐ Évaluer #{id}", "⭐ Valorar #{id}"),
    "rate_ask": ("Quantas estrelas para <b>{name}</b>?", "How many stars for <b>{name}</b>?", "Combien d'étoiles pour <b>{name}</b> ?", "¿Cuántas estrellas para <b>{name}</b>?"),
    "rate_comment": ("✍️ Escreva um comentário sobre o serviço (ou pule):", "✍️ Write a comment about the service (or skip):",
                     "✍️ Écrivez un commentaire (ou passez) :", "✍️ Escribe un comentario (u omite):"),
    "rate_thanks": ("🙏 Obrigado pela avaliação!", "🙏 Thanks for your review!", "🙏 Merci pour votre avis !", "🙏 ¡Gracias por tu valoración!"),
    "rate_not_allowed": ("Só é possível avaliar depois de um serviço concluído, uma vez por serviço.",
                         "You can only review a completed job, once per job.",
                         "Avis possible uniquement après une mission terminée, une fois.",
                         "Solo se puede valorar un trabajo completado, una vez."),
    "new_review_notify": ("⭐ Nova avaliação: {stars}\n{comment}", "⭐ New review: {stars}\n{comment}", "⭐ Nouvel avis : {stars}\n{comment}", "⭐ Nueva valoración: {stars}\n{comment}"),
    # ---------- denúncias / suporte ----------
    "report_ask": ("🚩 Descreva o motivo da denúncia:", "🚩 Describe the reason for the report:", "🚩 Décrivez le motif du signalement :", "🚩 Describe el motivo de la denuncia:"),
    "report_sent": ("✅ Denúncia enviada à moderação. Obrigado.", "✅ Report sent to moderation. Thank you.",
                    "✅ Signalement envoyé à la modération. Merci.", "✅ Denuncia enviada a moderación. Gracias."),
    "support_text": ("🆘 <b>Suporte</b>\n\nPrecisa de ajuda? Envie-nos uma mensagem e respondemos aqui no bot.\n\n"
                     "📄 <a href=\"{terms}\">Termos</a> · 🔒 <a href=\"{privacy}\">Privacidade</a>",
                     "🆘 <b>Support</b>\n\nNeed help? Send us a message and we'll reply here in the bot.\n\n"
                     "📄 <a href=\"{terms}\">Terms</a> · 🔒 <a href=\"{privacy}\">Privacy</a>",
                     "🆘 <b>Assistance</b>\n\nBesoin d'aide ? Envoyez-nous un message, nous répondrons ici.\n\n"
                     "📄 <a href=\"{terms}\">Conditions</a> · 🔒 <a href=\"{privacy}\">Confidentialité</a>",
                     "🆘 <b>Soporte</b>\n\n¿Necesitas ayuda? Envíanos un mensaje y responderemos aquí.\n\n"
                     "📄 <a href=\"{terms}\">Términos</a> · 🔒 <a href=\"{privacy}\">Privacidad</a>"),
    "btn.contact_support": ("✉️ Escrever ao suporte", "✉️ Write to support", "✉️ Écrire à l'assistance", "✉️ Escribir a soporte"),
    "support_ask": ("✍️ Escreva a sua mensagem para o suporte:", "✍️ Write your message to support:", "✍️ Écrivez votre message :", "✍️ Escribe tu mensaje para soporte:"),
    "support_sent": ("✅ Mensagem enviada! Responderemos o mais rápido possível.", "✅ Message sent! We'll reply as soon as possible.",
                     "✅ Message envoyé ! Nous répondrons au plus vite.", "✅ ¡Mensaje enviado! Responderemos lo antes posible."),
    "support_reply": ("🆘 <b>Resposta do suporte</b>:\n{text}", "🆘 <b>Support reply</b>:\n{text}", "🆘 <b>Réponse de l'assistance</b> :\n{text}", "🆘 <b>Respuesta de soporte</b>:\n{text}"),
    # ---------- perfil ----------
    "profile_text": ("👤 <b>{name}</b>\n📍 {city}\n🌐 {language}\n💳 Plano: {plan}\n🔔 Comunicados: {ann}\n📅 Membro desde {since}",
                     "👤 <b>{name}</b>\n📍 {city}\n🌐 {language}\n💳 Plan: {plan}\n🔔 Announcements: {ann}\n📅 Member since {since}",
                     "👤 <b>{name}</b>\n📍 {city}\n🌐 {language}\n💳 Formule : {plan}\n🔔 Annonces : {ann}\n📅 Membre depuis {since}",
                     "👤 <b>{name}</b>\n📍 {city}\n🌐 {language}\n💳 Plan: {plan}\n🔔 Comunicados: {ann}\n📅 Miembro desde {since}"),
    "on": ("ligado", "on", "activé", "activado"),
    "off": ("desligado", "off", "désactivé", "desactivado"),
    "btn.edit_name": ("✏️ Alterar nome", "✏️ Edit name", "✏️ Modifier le nom", "✏️ Cambiar nombre"),
    "btn.edit_provider": ("🧰 Editar perfil profissional", "🧰 Edit professional profile", "🧰 Modifier le profil pro", "🧰 Editar perfil profesional"),
    "btn.add_portfolio": ("🖼 Adicionar fotos ao portfólio", "🖼 Add portfolio photos", "🖼 Ajouter des photos", "🖼 Añadir fotos al portafolio"),
    "btn.clear_portfolio": ("🗑 Limpar portfólio", "🗑 Clear portfolio", "🗑 Vider le portfolio", "🗑 Vaciar portafolio"),
    "btn.toggle_notify": ("🔔 Notificações de pedidos: {state}", "🔔 Job notifications: {state}", "🔔 Notifications : {state}", "🔔 Notificaciones de pedidos: {state}"),
    "btn.toggle_ann": ("📣 Comunicados: {state}", "📣 Announcements: {state}", "📣 Annonces : {state}", "📣 Comunicados: {state}"),
    "btn.share_profile": ("📤 Partilhar meu perfil", "📤 Share my profile", "📤 Partager mon profil", "📤 Compartir mi perfil"),
    "btn.plans": ("💳 Planos", "💳 Plans", "💳 Formules", "💳 Planes"),
    "btn.export": ("📦 Exportar meus dados", "📦 Export my data", "📦 Exporter mes données", "📦 Exportar mis datos"),
    "btn.delete_account": ("🗑 Excluir conta", "🗑 Delete account", "🗑 Supprimer le compte", "🗑 Eliminar cuenta"),
    "delete_confirm": ("⚠️ Tem certeza? Todos os seus dados pessoais, pedidos, mensagens e perfil serão apagados definitivamente (RGPD).",
                       "⚠️ Are you sure? All your personal data, requests, messages and profile will be permanently deleted (GDPR).",
                       "⚠️ Êtes-vous sûr ? Toutes vos données, demandes, messages et profil seront supprimés définitivement (RGPD).",
                       "⚠️ ¿Seguro? Todos tus datos, pedidos, mensajes y perfil se eliminarán definitivamente (RGPD)."),
    "btn.delete_yes": ("🗑 Sim, excluir tudo", "🗑 Yes, delete everything", "🗑 Oui, tout supprimer", "🗑 Sí, eliminar todo"),
    "deleted": ("Sua conta e os seus dados foram excluídos. Até breve! Envie /start para voltar quando quiser.",
                "Your account and data were deleted. Send /start any time to come back.",
                "Votre compte et vos données ont été supprimés. Envoyez /start pour revenir.",
                "Tu cuenta y tus datos fueron eliminados. Envía /start para volver cuando quieras."),
    "ask_new_name": ("Envie o novo nome:", "Send the new name:", "Envoyez le nouveau nom :", "Envía el nuevo nombre:"),
    "saved": ("✅ Guardado.", "✅ Saved.", "✅ Enregistré.", "✅ Guardado."),
    "prov.ask_business": ("🧰 Nome profissional ou da empresa:", "🧰 Professional or company name:", "🧰 Nom professionnel ou de l'entreprise :", "🧰 Nombre profesional o de la empresa:"),
    "prov.ask_photo": ("🖼 Envie uma foto de perfil (ou pule):", "🖼 Send a profile photo (or skip):", "🖼 Envoyez une photo de profil (ou passez) :", "🖼 Envía una foto de perfil (u omite):"),
    "prov.ask_description": ("📝 Descreva a sua experiência e serviços:", "📝 Describe your experience and services:",
                             "📝 Décrivez votre expérience et vos services :", "📝 Describe tu experiencia y servicios:"),
    "prov.ask_categories": ("🏷 Escolha as suas especialidades (pode marcar várias) e toque em «Concluir»:",
                            "🏷 Choose your specialties (select several) then tap «Done»:",
                            "🏷 Choisissez vos spécialités (plusieurs possibles) puis « Terminer » :",
                            "🏷 Elige tus especialidades (puedes marcar varias) y toca «Listo»:"),
    "prov.need_category": ("Escolha pelo menos uma especialidade.", "Pick at least one specialty.", "Choisissez au moins une spécialité.", "Elige al menos una especialidad."),
    "prov.ask_radius": ("📏 Raio de atendimento:", "📏 Service radius:", "📏 Rayon d'intervention :", "📏 Radio de servicio:"),
    "prov.ask_price_type": ("💶 Como cobra?", "💶 How do you charge?", "💶 Comment facturez-vous ?", "💶 ¿Cómo cobras?"),
    "btn.price_hourly": ("⏱ Preço por hora", "⏱ Hourly rate", "⏱ Tarif horaire", "⏱ Precio por hora"),
    "btn.price_quote": ("📄 Orçamento personalizado", "📄 Custom quote", "📄 Devis personnalisé", "📄 Presupuesto personalizado"),
    "prov.ask_rate": ("Valor por hora em euros (ex.: 20):", "Hourly rate in euros (e.g. 20):", "Tarif horaire en euros (ex. : 20) :", "Precio por hora en euros (ej.: 20):"),
    "prov.bad_rate": ("Envie apenas um número, ex.: 20", "Send a number only, e.g. 20", "Envoyez un nombre, ex. : 20", "Envía solo un número, ej.: 20"),
    "prov.ask_availability": ("🗓 Disponibilidade (ex.: seg–sex 9h–18h, fins de semana):", "🗓 Availability (e.g. Mon–Fri 9–6, weekends):",
                              "🗓 Disponibilités (ex. : lun–ven 9h–18h, week-ends) :", "🗓 Disponibilidad (ej.: lun–vie 9–18h, fines de semana):"),
    "prov.done": ("🎉 Perfil profissional guardado! Você receberá pedidos compatíveis automaticamente.",
                  "🎉 Professional profile saved! You'll receive matching jobs automatically.",
                  "🎉 Profil professionnel enregistré ! Vous recevrez automatiquement les demandes compatibles.",
                  "🎉 ¡Perfil profesional guardado! Recibirás pedidos compatibles automáticamente."),
    "portfolio_ask": ("🖼 Envie as fotos do portfólio (até 10 no total). Toque em «Concluir» quando terminar.",
                      "🖼 Send portfolio photos (up to 10 total). Tap «Done» when finished.",
                      "🖼 Envoyez vos photos (10 max). Touchez « Terminer » à la fin.",
                      "🖼 Envía fotos del portafolio (hasta 10). Toca «Listo» al terminar."),
    "portfolio_full": ("O portfólio já tem 10 fotos.", "Portfolio already has 10 photos.", "Le portfolio a déjà 10 photos.", "El portafolio ya tiene 10 fotos."),
    # ---------- convites ----------
    "invite_text": ("👥 <b>Convide amigos para o ServiceConnect</b>\n\nO seu link pessoal:\n<code>{link}</code>\n\n"
                    "📈 Convites: <b>{total}</b> · válidos: <b>{valid}</b>\n🏆 A sua posição no ranking: <b>{rank}</b>\n\n"
                    "🎁 Os primeiros usuários e quem mais convidar terão benefícios exclusivos quando lançarmos os planos.\n\n<b>Top 10</b>\n{top}",
                    "👥 <b>Invite friends to ServiceConnect</b>\n\nYour personal link:\n<code>{link}</code>\n\n"
                    "📈 Invites: <b>{total}</b> · valid: <b>{valid}</b>\n🏆 Your ranking: <b>{rank}</b>\n\n"
                    "🎁 Early users and top inviters will get exclusive benefits when plans launch.\n\n<b>Top 10</b>\n{top}",
                    "👥 <b>Invitez des amis sur ServiceConnect</b>\n\nVotre lien personnel :\n<code>{link}</code>\n\n"
                    "📈 Invitations : <b>{total}</b> · valides : <b>{valid}</b>\n🏆 Votre classement : <b>{rank}</b>\n\n"
                    "🎁 Les premiers utilisateurs et meilleurs parrains auront des avantages exclusifs.\n\n<b>Top 10</b>\n{top}",
                    "👥 <b>Invita amigos a ServiceConnect</b>\n\nTu enlace personal:\n<code>{link}</code>\n\n"
                    "📈 Invitaciones: <b>{total}</b> · válidas: <b>{valid}</b>\n🏆 Tu posición: <b>{rank}</b>\n\n"
                    "🎁 Los primeros usuarios y quienes más inviten tendrán beneficios exclusivos.\n\n<b>Top 10</b>\n{top}"),
    "share_invite_msg": ("Encontre profissionais ou trabalho perto de você, grátis, no ServiceConnect 👇",
                         "Find professionals or work near you, for free, on ServiceConnect 👇",
                         "Trouvez des pros ou du travail près de chez vous, gratuitement, sur ServiceConnect 👇",
                         "Encuentra profesionales o trabajo cerca de ti, gratis, en ServiceConnect 👇"),
    "btn.share_invite": ("📤 Partilhar convite", "📤 Share invite", "📤 Partager l'invitation", "📤 Compartir invitación"),
    "referral_joined": ("🎉 Alguém entrou com o seu link de convite!", "🎉 Someone joined with your invite link!",
                        "🎉 Quelqu'un a rejoint avec votre lien !", "🎉 ¡Alguien se unió con tu enlace!"),
    # ---------- idioma ----------
    "choose_language": ("🌐 Escolha o idioma:", "🌐 Choose your language:", "🌐 Choisissez la langue :", "🌐 Elige el idioma:"),
    "language_set": ("✅ Idioma alterado.", "✅ Language changed.", "✅ Langue modifiée.", "✅ Idioma cambiado."),
    # ---------- planos ----------
    "plans_free": ("💚 <b>O ServiceConnect é 100% gratuito</b> neste momento: cadastro, pedidos, propostas e mensagens ilimitados, sem comissões.\n\n"
                   "No futuro poderão existir planos opcionais com benefícios extra (destaque, estatísticas…). "
                   "Você será avisado com antecedência e <b>nada será cobrado sem a sua autorização expressa</b>.",
                   "💚 <b>ServiceConnect is 100% free</b> right now: unlimited sign-up, requests, proposals and messages, no commission.\n\n"
                   "Optional plans with extra benefits may come later. You'll be informed in advance and "
                   "<b>nothing will ever be charged without your explicit consent</b>.",
                   "💚 <b>ServiceConnect est 100 % gratuit</b> pour l'instant : inscription, demandes, propositions et messages illimités, sans commission.\n\n"
                   "Des formules optionnelles pourront arriver. Vous serez prévenu à l'avance et "
                   "<b>rien ne sera facturé sans votre accord explicite</b>.",
                   "💚 <b>ServiceConnect es 100% gratis</b> ahora mismo: registro, pedidos, propuestas y mensajes ilimitados, sin comisiones.\n\n"
                   "En el futuro podrá haber planes opcionales. Te avisaremos con antelación y "
                   "<b>nunca se cobrará nada sin tu autorización expresa</b>."),
    "plans_list": ("💳 <b>Planos</b> (o plano Gratuito continua disponível)\nO seu plano: <b>{current}</b>\n\n{plans}",
                   "💳 <b>Plans</b> (the Free plan remains available)\nYour plan: <b>{current}</b>\n\n{plans}",
                   "💳 <b>Formules</b> (la formule Gratuite reste disponible)\nVotre formule : <b>{current}</b>\n\n{plans}",
                   "💳 <b>Planes</b> (el plan Gratuito sigue disponible)\nTu plan: <b>{current}</b>\n\n{plans}"),
    "plan_consent": ("Você está prestes a assinar <b>{plan}</b> por <b>{stars} ⭐ Telegram Stars</b> (≈ {eur} €) por 30 dias.\n"
                     "Não há renovação automática sem nova autorização. Confirma?",
                     "You're about to subscribe to <b>{plan}</b> for <b>{stars} ⭐ Telegram Stars</b> (≈ €{eur}) for 30 days.\n"
                     "No automatic renewal without new authorization. Confirm?",
                     "Vous allez souscrire à <b>{plan}</b> pour <b>{stars} ⭐ Telegram Stars</b> (≈ {eur} €) pour 30 jours.\n"
                     "Pas de renouvellement automatique sans nouvelle autorisation. Confirmer ?",
                     "Vas a suscribirte a <b>{plan}</b> por <b>{stars} ⭐ Telegram Stars</b> (≈ {eur} €) durante 30 días.\n"
                     "No hay renovación automática sin nueva autorización. ¿Confirmas?"),
    "btn.subscribe": ("Assinar {plan}", "Subscribe {plan}", "Souscrire {plan}", "Suscribirse a {plan}"),
    "plan_activated": ("🎉 Plano <b>{plan}</b> ativo até {until}. Obrigado!", "🎉 Plan <b>{plan}</b> active until {until}. Thank you!",
                       "🎉 Formule <b>{plan}</b> active jusqu'au {until}. Merci !", "🎉 Plan <b>{plan}</b> activo hasta {until}. ¡Gracias!"),
    "btn.promo": ("🎟 Tenho um código promocional", "🎟 I have a promo code", "🎟 J'ai un code promo", "🎟 Tengo un código promocional"),
    "promo_ask": ("Envie o código promocional:", "Send the promo code:", "Envoyez le code promo :", "Envía el código promocional:"),
    "promo_invalid": ("Código inválido, expirado ou já usado.", "Invalid, expired or already used code.", "Code invalide, expiré ou déjà utilisé.", "Código inválido, caducado o ya usado."),
    "monetization_off": ("Os pagamentos estão desativados — tudo é gratuito. 💚", "Payments are disabled — everything is free. 💚",
                         "Les paiements sont désactivés — tout est gratuit. 💚", "Los pagos están desactivados — todo es gratis. 💚"),
    "announcement": ("📣 <b>Comunicado ServiceConnect</b>\n\n{text}\n\n<i>Para deixar de receber: 👤 Meu perfil → 📣 Comunicados.</i>",
                     "📣 <b>ServiceConnect announcement</b>\n\n{text}\n\n<i>To stop receiving these: 👤 My profile → 📣 Announcements.</i>",
                     "📣 <b>Annonce ServiceConnect</b>\n\n{text}\n\n<i>Pour ne plus recevoir : 👤 Mon profil → 📣 Annonces.</i>",
                     "📣 <b>Comunicado de ServiceConnect</b>\n\n{text}\n\n<i>Para dejar de recibirlos: 👤 Mi perfil → 📣 Comunicados.</i>"),
    "help": ("Use os botões do menu. Comandos: /start · /menu · /cancel · /help", "Use the menu buttons. Commands: /start · /menu · /cancel · /help",
             "Utilisez les boutons du menu. Commandes : /start · /menu · /cancel · /help", "Usa los botones del menú. Comandos: /start · /menu · /cancel · /help"),
}

# planos: nome traduzido
PLAN_NAMES = {
    "free": {"pt": "Gratuito", "en": "Free", "fr": "Gratuit", "es": "Gratuito"},
    "pro": {"pt": "Profissional", "en": "Professional", "fr": "Professionnel", "es": "Profesional"},
    "premium": {"pt": "Premium", "en": "Premium", "fr": "Premium", "es": "Premium"},
    "business": {"pt": "Empresa", "en": "Business", "fr": "Entreprise", "es": "Empresa"},
}


def norm_lang(code: str | None) -> str:
    code = (code or "").lower()[:2]
    return code if code in LANGS else "en" if code else "pt"


def t(key: str, lang: str = "pt", **kwargs) -> str:
    row = _T.get(key)
    if row is None:
        return key
    idx = LANGS.index(lang) if lang in LANGS else 0
    text = row[idx] or row[0]
    return text.format(**kwargs) if kwargs else text


def all_variants(key: str) -> set[str]:
    return set(_T[key])


MENU_KEYS = ("menu.find", "menu.publish", "menu.jobs", "menu.profile", "menu.requests", "menu.messages",
             "menu.reviews", "menu.location", "menu.invite", "menu.language", "menu.support")

# texto do botão (qualquer idioma) -> chave
MENU_LOOKUP: dict[str, str] = {variant: key for key in MENU_KEYS for variant in _T[key]}


def missing_translations() -> list[str]:
    return [k for k, row in _T.items() if len(row) != 4 or any(not x for x in row)]
