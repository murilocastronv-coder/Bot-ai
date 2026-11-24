import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";
import type { User } from "@prisma/client";
import { config } from "./config.js";
import { prisma } from "./db.js";

declare global { namespace Express { interface Request { user?: User; businessId?: string } } }

export const COOKIE = "sb_token";
export function issueSession(res: Response, userId: string) {
  const token = jwt.sign({ uid: userId }, config.jwtSecret, { expiresIn: "7d" });
  res.cookie(COOKIE, token, { httpOnly: true, secure: config.isProd, sameSite: "lax", maxAge: 7 * 86400000, path: "/" });
}
export function verifyToken(token: string | undefined): string | null {
  if (!token) return null;
  try { return (jwt.verify(token, config.jwtSecret) as { uid: string }).uid; } catch { return null; }
}

export async function requireAuth(req: Request, res: Response, next: NextFunction) {
  const uid = verifyToken(req.cookies?.[COOKIE]);
  const user = uid ? await prisma.user.findUnique({ where: { id: uid } }) : null;
  if (!user) return res.status(401).json({ error: "Não autenticado" });
  req.user = user;
  req.businessId = user.businessId ?? undefined;
  next();
}
export function requireBusiness(req: Request, res: Response, next: NextFunction) {
  if (!req.businessId) return res.status(403).json({ error: "Sem empresa associada" });
  next();
}
export function requireSuperadmin(req: Request, res: Response, next: NextFunction) {
  if (req.user?.role !== "SUPERADMIN") return res.status(403).json({ error: "Acesso restrito" });
  next();
}
/** Erros de validação zod -> 400 */
export const asyncH = (fn: (req: Request, res: Response) => Promise<unknown>) =>
  (req: Request, res: Response, next: NextFunction) => fn(req, res).catch(next);
