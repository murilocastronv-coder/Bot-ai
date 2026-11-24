# SmartBusiness AI

Plataforma SaaS que oferece agentes de IA para pequenas e médias empresas. Cada empresa configura o próprio agente, que atende os clientes 24h/24 no **site (widget)**, no **Telegram** e no **WhatsApp (API oficial da Meta)**, agenda horários, registra orçamentos e passa a conversa para um humano quando precisa.

> **Deploy gratuito:** o `render.yaml` deste repositório usa o plano free do Render e a IA gratuita da Groq. Veja “Modo gratuito” abaixo.

## Estado atual (MVP)

| Funcionalidade | Estado | Como foi verificado |
|---|---|---|
| Cadastro, verificação de e-mail, login, recuperação de senha | ✅ | testes automatizados + navegador |
| Isolamento de dados entre empresas | ✅ | testes automatizados (tentativas de acesso cruzado) |
| Agente de IA (OpenAI) com base de conhecimento por empresa | ✅ | testes com respostas no formato oficial da OpenAI ⚠️ ainda não testado com chave real |
| Ferramentas do agente: contato, orçamento, disponibilidade, agendar, listar, cancelar, transferir para humano | ✅ | testes automatizados |
| Detecção de idioma FR / PT / EN / ES | ✅ | testes |
| Proteção contra prompt injection | ✅ | ferramentas limitadas ao cliente da conversa, testado |
| Widget para sites externos | ✅ | navegador, a partir de outra origem |
| Telegram Bot API | ✅ | testes com o formato oficial da API ⚠️ falta testar com um bot real |
| WhatsApp Business Cloud API | ✅ | testes de assinatura e envio ⚠️ falta testar com conta Meta real |
| Atendimento humano manual + tempo real (WebSocket) | ✅ | navegador |
| CRM, orçamentos, exportação CSV, consentimento comercial | ✅ | testes + navegador |
| Agenda (calendário) + lembretes automáticos | ✅ | testes |
| Stripe: checkout, portal, webhooks verificados, cupons | ✅ | testes do webhook assinado ⚠️ falta testar o checkout em modo teste real |
| Limites por plano, teste de 7 dias, controle de custos | ✅ | testes |
| Painel admin: empresas, MRR, faturamento, custos, bloqueio, planos, cupons, erros, servidor | ✅ | testes |
| RGPD: exportação, exclusão de conta e de clientes, política de privacidade | ✅ | testes |
| Instagram, Messenger, Google Calendar, vários funcionários por conta | 🔜 próximas fases | — |

**⚠️ = o código usa a API real, mas só foi testado com respostas que imitam a API oficial.** Para considerar a integração concluída, faça o teste real descrito em “Checklist de testes reais”.

## Como funciona o Telegram

Cada empresa cria **o próprio bot** no Telegram (de graça) e o conecta em *Canais*:

1. No Telegram, abra **@BotFather** → `/newbot` → escolha nome e usuário (terminado em `bot`).
2. Copie o token e cole em **Canais → Telegram** no painel.
3. A plataforma valida o token (`getMe`), registra o webhook (`setWebhook` com `secret_token`) e guarda o token criptografado (AES-256-GCM).
4. Os clientes conversam com `t.me/<usuario_do_bot>`: o agente responde, agenda, cria orçamentos e envia lembretes pelo próprio Telegram.

Não é preciso pedir aprovação ao Telegram. Limitações: o bot só responde **conversas privadas** e só pode escrever a quem já falou com ele.

## Modo gratuito (como está publicado)

| Item | Gratuito | Limitação |
|---|---|---|
| Hospedagem | Render, plano **free** | Hiberna após 15 min sem acesso; a 1ª mensagem depois disso demora ~1 min (o Telegram reenvia sozinho). Para ficar sempre acordado, cadastre `https://SEU-APP.onrender.com/health` num monitor grátis (ex.: cron-job.org ou UptimeRobot) a cada 10 min. |
| IA | **Groq** (`llama-3.3-70b-versatile`): chave grátis, sem cartão, em https://console.groq.com/keys | Limites diários do plano grátis. Alternativa: Google Gemini (`AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`, `AI_MODEL=gemini-2.0-flash`). |
| Banco | Esquema `botai` no PostgreSQL já existente | — |
| E-mail | `EMAIL_VERIFICATION=off` | Sem confirmação de e-mail nem recuperação de senha por e-mail. |

As variáveis `BOOTSTRAP_*` e `TELEGRAM_BOT_TOKEN` criam automaticamente, na primeira inicialização, a conta do dono (administrador, plano Business), o negócio, e conectam o bot do Telegram.

## Arquitetura

```
./
├── server/                 Node.js + TypeScript + Express + Prisma + WebSocket
│   ├── prisma/             schema + migrations (PostgreSQL)
│   ├── src/agent/          motor do agente, prompt, ferramentas, modelos por setor, idioma, fusos
│   ├── src/channels/       Telegram, WhatsApp, envio unificado
│   ├── src/routes/         auth, empresa, CRM, faturamento, webhooks, widget, admin, RGPD
│   ├── src/services/       Stripe, lembretes
│   └── test/               testes de integração (Vitest + Supertest + PostgreSQL real)
└── web/                    React + TypeScript + Tailwind (Vite), mobile-first
```

- Um único serviço web no Render serve a API, os webhooks, o WebSocket (`/ws`), o `widget.js` e o frontend compilado.
- Todas as mensagens, de qualquer canal, passam por `handleIncoming()` (`server/src/agent/engine.ts`).
- Chaves de API ficam só no servidor. O frontend nunca recebe tokens (testado).

## Rodar localmente

Requisitos: Node 20+ e PostgreSQL 14+.

```bash
cd server
cp ../.env.example .env        # preencha DATABASE_URL e, se quiser, OPENAI_API_KEY
npm install
npx prisma migrate deploy
npm run dev                    # API em http://localhost:3000

cd ../web
npm install
npm run dev                    # frontend em http://localhost:5173 (proxy para a API)
```

Sem `SMTP_URL` (só fora de produção) os e-mails de verificação aparecem no terminal do servidor.

### Testes

```bash
cd server
createdb sb_test
TEST_DATABASE_URL=postgresql://USER@localhost:5432/sb_test npm test
```

A suíte **apaga e recria** o banco de testes. Os testes de integração usam PostgreSQL real; as APIs externas (OpenAI, Telegram, Meta) são interceptadas na camada HTTP com respostas no formato oficial de cada uma; os webhooks Stripe usam assinaturas reais geradas pelo SDK. O GitHub Actions (`.github/workflows/ci.yml`) roda tudo a cada push.

## Deploy no Render

1. Render → **New → Blueprint** → selecione este repositório (`render.yaml` na raiz).
2. Preencha as variáveis marcadas como `sync: false` (veja a tabela abaixo).
3. Depois do primeiro deploy, configure os webhooks externos com a URL final (`APP_URL`).
4. Cadastre-se com um e-mail listado em `SUPERADMIN_EMAILS` para ter acesso a `/app/admin`.

As migrações rodam automaticamente a cada deploy (`prisma migrate deploy`). O serviço web usa o plano **starter** porque o plano free hiberna e deixaria o agente fora do ar. O banco usa um plano pago, que inclui **backups automáticos**. Se quiser uma cópia extra fora do Render, agende um `pg_dump` para um armazenamento externo.

## Credenciais, permissões e aprovações externas

| Serviço | O que obter | Onde configurar | Aprovação externa |
|---|---|---|---|
| **OpenAI** | API key com créditos/faturamento ativo | `OPENAI_API_KEY` | Não |
| **Stripe** | Secret key; 3 *Prices* recorrentes mensais em EUR (19,90 / 49,90 / 99,90); endpoint de webhook `{APP_URL}/webhooks/stripe` com os eventos `checkout.session.completed`, `customer.subscription.created/updated/deleted`, `invoice.payment_failed`; ativar o **Customer Portal** (cancelamento e troca de plano) | `STRIPE_*` | Ativação da conta Stripe (dados da empresa e bancários) para cobrar de verdade |
| **WhatsApp Cloud API** | App em developers.facebook.com com o produto WhatsApp; webhook `{APP_URL}/webhooks/whatsapp` com o token `WHATSAPP_VERIFY_TOKEN`, assinando o campo `messages`; App Secret | `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` | **Sim**: verificação do Meta Business, número verificado, **App Review** com as permissões `whatsapp_business_messaging` e `whatsapp_business_management` para atender outras empresas (modelo Tech Provider) e app em modo *Live* |
| WhatsApp, cada empresa cliente | Phone Number ID + token permanente de *System User* | Painel → Canais | Número dedicado e verificado; nomes de exibição aprovados pela Meta |
| **Telegram**, cada empresa cliente | Token do @BotFather | Painel → Canais | Não |
| **E-mail (SMTP)** | Provedor transacional (Brevo, Postmark, SES, Resend SMTP…) com domínio verificado (SPF/DKIM) | `SMTP_URL`, `MAIL_FROM` | Verificação do domínio no provedor |
| **Render** | Conta com cartão (planos pagos) | — | Não |

Regras das plataformas que o código já respeita:

- **WhatsApp:** texto livre só pode ser enviado até 24h depois da última mensagem do cliente. Lembretes fora dessa janela precisam de *templates* aprovados pela Meta; enquanto isso, a plataforma **não envia** e registra o motivo no log de erros.
- **Telegram:** só responde conversas privadas, com `secret_token` em cada webhook.
- **Stripe:** cada evento é verificado pela assinatura e processado uma única vez (idempotência).

## Checklist de testes reais (antes de vender)

1. **OpenAI:** configure a chave, cadastre serviços e preços, converse pelo widget e confirme que preços não cadastrados não são inventados.
2. **Telegram:** crie um bot de teste, conecte (plano Professional; o admin pode mudar o plano em `/app/admin`), envie `/start`, agende um horário e confira a agenda.
3. **WhatsApp:** com o número de teste da Meta, envie uma mensagem ao número e confirme a resposta e o contato criado no CRM.
4. **Stripe (modo teste):** assine com o cartão `4242 4242 4242 4242`, confirme que o plano mudou, cancele pelo portal e confirme a volta ao plano Gratuito.
5. **E-mail:** cadastro real com recebimento do link de verificação e da redefinição de senha.

## Segurança e RGPD

- Senhas com bcrypt (custo 12); sessão JWT em cookie `httpOnly`, `SameSite=Lax`, `Secure` em produção.
- Tokens do Telegram e do WhatsApp criptografados com AES-256-GCM (`ENCRYPTION_KEY`).
- Toda consulta filtrada por `businessId` da sessão; as ferramentas da IA só agem sobre o contato da conversa atual.
- Rate limiting (login, cadastro, API, widget), honeypot anti-spam, Helmet/CSP, limite de tamanho das mensagens.
- Prompt injection: dados da empresa delimitados e tratados como dados, regras não alteráveis, detecção e registro de tentativas, validação no servidor de todo argumento de ferramenta.
- Exportação e exclusão da conta (com cascata) e de clientes finais individualmente; consentimento comercial registrado com data; CSV protegido contra injeção de fórmulas.
- Política de privacidade e termos (`/privacy`, `/terms`) são **modelos**: complete com os dados do responsável legal e revise com um jurista.

## Próximas fases

1. Instagram Messaging e Facebook Messenger (mesma infraestrutura de webhook da Meta; exigem App Review de `instagram_manage_messages` / `pages_messaging`).
2. Google Calendar (OAuth por empresa; sincronização de disponibilidade e eventos; exige verificação do app OAuth pelo Google).
3. Vários funcionários por empresa e vários agentes (plano Business): convites e papéis.
4. Templates de WhatsApp aprovados para lembretes fora da janela de 24h.
5. Painel do empresário em FR/EN/ES (a landing page já está nos 4 idiomas).
6. Busca semântica com embeddings (pgvector) para bases de conhecimento grandes.
