import http from "node:http";
import { WebSocketServer } from "ws";
import { createApp } from "./app.js";
import { config } from "./lib/config.js";
import { COOKIE, verifyToken } from "./lib/auth.js";
import { prisma } from "./lib/db.js";
import { bizKey, subscribe } from "./lib/realtime.js";
import { startReminderLoop } from "./services/reminders.js";
import { runBootstrap } from "./services/bootstrap.js";

const app = createApp();
const server = http.createServer(app);

// WebSocket do painel: atualizações em tempo real das conversas da empresa
const wss = new WebSocketServer({ noServer: true });
server.on("upgrade", async (req, socket, head) => {
  if (!req.url?.startsWith("/ws")) return socket.destroy();
  const cookies = Object.fromEntries((req.headers.cookie ?? "").split(";").map((c) => c.trim().split("=").map(decodeURIComponent)));
  const uid = verifyToken(cookies[COOKIE]);
  const user = uid ? await prisma.user.findUnique({ where: { id: uid } }) : null;
  if (!user?.businessId) { socket.write("HTTP/1.1 401 Unauthorized\r\n\r\n"); return socket.destroy(); }
  wss.handleUpgrade(req, socket, head, (ws) => {
    subscribe(bizKey(user.businessId!), ws);
    const ping = setInterval(() => ws.readyState === 1 && ws.ping(), 30000);
    ws.on("close", () => clearInterval(ping));
  });
});

startReminderLoop();
runBootstrap();
server.listen(config.port, () => console.log(`SmartBusiness AI ouvindo em :${config.port}`));

const shutdown = () => { server.close(); prisma.$disconnect().finally(() => process.exit(0)); };
process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);
