# ServiceConnect — marketplace de serviços no Telegram

Bot de Telegram que conecta **clientes** e **profissionais** automaticamente: pedidos com fotos, busca por distância,
notificações aos profissionais compatíveis, orçamentos/propostas, chat interno, avaliações, convites virais,
painel administrativo web e monetização (Telegram Stars) **preparada mas desativada**.

- **100% gratuito no lançamento**: sem comissões, sem mensalidades, sem cartão.
- Funciona em Android, iPhone e computador (é o próprio Telegram).
- Idiomas: 🇵🇹 Português · 🇫🇷 Français · 🇬🇧 English · 🇪🇸 Español (detecção automática + troca manual).
- Python 3.12 · aiogram 3 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · webhooks · Docker · Render.

## Estrutura

| Ficheiro | Conteúdo |
|---|---|
| `main.py` | Servidor FastAPI: webhook do Telegram (`/telegram/webhook`, com segredo), `/health`, `/terms`, `/privacy`, painel; modo `--polling` para desenvolvimento |
| `bot.py` | Todos os menus, botões e fluxos do bot (aiogram 3) |
| `services.py` | Regras de negócio: busca geográfica, correspondência, propostas, contratação, avaliações, chat, indicações, RGPD, planos |
| `models.py` | Tabelas (usuários, perfis profissionais, portfólio, categorias, pedidos, propostas, conversas, mensagens, avaliações, denúncias, planos, assinaturas, promoções, cidades, configurações, comunicados, estado do bot) |
| `database.py` | Ligação PostgreSQL (aceita o `postgres://` do Render), esquema próprio, dados iniciais |
| `admin.py` + `templates/` | Painel administrativo responsivo |
| `i18n.py` | Traduções |
| `legal.py` | Termos de Utilização e Política de Privacidade (RGPD) nos 4 idiomas |
| `storage.py` | Estado das conversas guardado no PostgreSQL (não se perde quando o Render reinicia) |
| `tests/` | Testes automatizados |

## Robô SAM SOL (`/sol`, só administradores)

A estratégia do EA **SAM Style V4** (MT5) passada para SOL/USD: entra a favor de um movimento de 50 pontos
na vela de 1 minuto, no máximo 2 ordens do mesmo lado (a 2ª 80 pontos a favor), cesta com trailing de
US$ 1,00/0,30, stop de 1% do saldo por cesta, margem ≤ 15%, meta do mês +40% / stop do mês −5%.
O lucro das cestas já desconta as taxas da Jupiter (0,06% + 0,06%).

- **Conta demo**: liga sozinha, US$ 1000 de mentira com o preço real da Binance.
- **Conta real**: Jupiter Perps, começa **desligada**. 💼 Carteira real cria a carteira (precisa de
  `SAM_WALLET_PASSPHRASE`), envie USDC + ~0,05 SOL e confirme 💰 Ligar real.
- **Backtest**: 1 ano, 3 meses, 2 meses e 1 mês com velas de 1 minuto da Binance.

Código: `sam_sol.py` (estratégia, backtest, robô, botões), `sam_perps.py` (ordens na Jupiter), `sam_wallet.py`.

## Funcionalidades

**Menu principal**: 🔎 Encontrar profissional · 📢 Publicar um serviço · 💼 Encontrar trabalho · 👤 Meu perfil ·
📋 Minhas solicitações · 💬 Minhas mensagens · ⭐ Avaliações · 📍 Alterar localização · 👥 Convidar amigos · 🌐 Idioma · 🆘 Suporte

- **Cadastro**: aceite dos termos → nome → cliente ou profissional → cidade ou localização partilhada.
- **Perfil profissional**: nome/empresa, foto, descrição, especialidades (várias), raio (5–100 km), preço por hora ou orçamento, disponibilidade, portfólio (até 10 fotos), avaliações, selo ✅ verificado (atribuído pelo admin), contador de visualizações, link de partilha.
- **18 categorias** iniciais; o admin adiciona/edita/desativa outras (nomes nos 4 idiomas).
- **Pedidos**: categoria, descrição, até 5 fotos, cidade, orçamento, data, urgência. Os profissionais compatíveis (especialidade + dentro do raio deles, ou mesma cidade quando não há coordenadas) recebem a notificação automaticamente — quem desligou as notificações não recebe. Link para partilhar o pedido em grupos.
- **Propostas**: preço, disponibilidade, mensagem. O cliente compara (ordenadas por verificado, avaliação e preço), conversa e contrata; os outros são avisados. O profissional aceita ou recusa o trabalho (se recusar, o pedido reabre).
- **Chat interno**: texto e fotos, sem partilhar telefone nem @username; mensagens não lidas; histórico.
- **Avaliações** 1–5 ⭐ com comentário, só depois de o cliente marcar o serviço como concluído e uma por serviço; denúncia de avaliações, perfis e pedidos; moderação no painel.
- **Localização**: busca por cidade ou por 5/10/25/50/100 km; mais próximos primeiro; funciona em qualquer país; a posição exata nunca é mostrada.
- **Crescimento**: link de convite individual, contador, ranking de indicações **válidas** (só contam convidados com cadastro concluído e não suspensos), selo early adopter para os primeiros 1000, partilha de perfil e de pedidos.
- **Anti-spam**: limite de ações por minuto, de pedidos e propostas por dia, de notificações por pedido; suspensão de contas.
- **RGPD**: exportar os meus dados (JSON), excluir conta e todos os dados, opt-out de comunicados, termos e privacidade.

## Monetização (desativada por padrão)

- Planos editáveis no painel: Gratuito, Profissional (9,99 €), Premium (19,99 €), Empresa (39,99 €) + preço em ⭐ Telegram Stars.
- Enquanto estiver desativada, o bot mostra "100% gratuito" e **não existe nenhuma forma de pagar**.
- Para ativar: painel → 💳 Planos → escrever `ATIVAR`. Envie antes um comunicado aos usuários.
- Pagamento por Telegram Stars (exigido pelo Telegram para bens digitais), 30 dias, **sem renovação automática**; antes da fatura o usuário vê o preço e confirma.
- Benefícios já ligados ao plano: destaque nos resultados (⭐ Destaque), notificações prioritárias (recebe primeiro).
- O admin pode conceder premium grátis a qualquer usuário e criar códigos promocionais.

## Painel administrativo (`/admin`)

Login com `ADMIN_USERNAME` / `ADMIN_PASSWORD`, sessão assinada (12 h), proteção CSRF, bloqueio após 5 tentativas falhadas.

Painel com estatísticas (usuários, clientes, profissionais, ativos 24 h/7 d, pedidos, propostas, mensagens, receita) · usuários (pesquisa, filtros, suspender, verificar, conceder premium, excluir) · pedidos (remover) · categorias · denúncias e suporte (resolver, ocultar avaliação, suspender, responder pelo bot) · comunicados (só para quem aceita) · planos, preços e promoções · países e cidades · ranking de indicações · backup JSON.

Pelo Telegram, os IDs em `ADMIN_TELEGRAM_IDS` recebem denúncias e pedidos de suporte e podem usar `/admin` e `/reply <id> <texto>`.

## Deploy no Render

O `render.yaml` da raiz do repositório já declara o serviço **`serviceconnect-bot`** (Docker, pasta `serviceconnect/`), ligado ao PostgreSQL existente `solana-devbot-db` num esquema separado `serviceconnect` (não toca nas tabelas do bot-ai).

1. No Render: **Blueprints → (este repositório) → Sync** (ou automático no próximo push para `main`).
2. Preencha as variáveis pedidas:
   - `BOT_TOKEN` — token do @BotFather
   - `ADMIN_PASSWORD` — senha forte do painel
   - `ADMIN_TELEGRAM_IDS` — o seu ID do Telegram (ex.: pergunte a @userinfobot)
3. Pronto. No arranque o servidor cria as tabelas, as categorias, os planos e regista o webhook em `https://<serviço>.onrender.com/telegram/webhook`. `WEBHOOK_SECRET` e `SESSION_SECRET` são gerados pelo Render.

> **Plano free do Render**: o serviço adormece após 15 min sem tráfego; a primeira mensagem depois disso demora ~1 min (o Telegram reenvia sozinho). Para responder sempre na hora (24 h), use o plano Starter ou um monitor gratuito a chamar `/health` a cada 10 min.

**Backups**: o Render faz backups diários do PostgreSQL pago; além disso há `/admin/backup` (JSON) e `scripts_backup.sh` (pg_dump do esquema).

## Desenvolvimento local

```bash
cd serviceconnect
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # preencha BOT_TOKEN; sem DATABASE_URL usa SQLite local
set -a && . ./.env && set +a
python main.py --polling          # bot por long polling
uvicorn main:app --reload         # painel em http://localhost:8000/admin
```

## Testes

```bash
python -m pytest -q                                                       # SQLite
TEST_DATABASE_URL=postgresql://postgres@localhost:5432/test python -m pytest -q   # PostgreSQL real
```

Cobrem: traduções completas; busca por categoria/distância/cidade e ordenação; ciclo completo pedido → propostas → contratação → recusa/reabertura → conclusão → avaliação (e as proibições); limites anti-spam; indicações válidas; chat e permissões; exportação e exclusão RGPD; promoções; estado persistente do bot; **simulação do bot completo** (cadastro de cliente e profissional, busca, publicação com notificação, proposta, chat, contratação, avaliação, todos os botões do menu, denúncia, suporte, idioma, planos desativados, exclusão de conta, usuário suspenso, idioma automático); painel (login, CSRF, todas as páginas, categorias, preços, promoções, cidades, monetização com confirmação, moderação, backup) e webhook com segredo.
