/**
 * POST /api/admin/login — autentica com senha e define cookie de sessão.
 * A senha é comparada SERVER-SIDE. Nunca exposta ao browser.
 *
 * INSTALAR NO SITE VERCEL: copiar para /app/api/admin/login/route.ts
 */

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const COOKIE_SESSAO = "freelance_bot_sessao";
const MAX_AGE = 60 * 60 * 24 * 7; // 7 dias

export async function POST(request: NextRequest) {
  const { senha } = await request.json();
  const senhaCorreta = process.env.ADMIN_PASSWORD;

  if (!senhaCorreta) {
    return NextResponse.json(
      { erro: "ADMIN_PASSWORD não configurado no servidor." },
      { status: 500 }
    );
  }

  if (senha !== senhaCorreta) {
    return NextResponse.json({ erro: "Senha incorreta." }, { status: 401 });
  }

  // gera token de sessão simples (suficiente para uso pessoal)
  const tokenSessao = Buffer.from(
    `${Date.now()}:${Math.random()}`
  ).toString("base64");

  const cookieStore = await cookies();
  cookieStore.set(COOKIE_SESSAO, tokenSessao, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: MAX_AGE,
    path: "/",
  });

  return NextResponse.json({ ok: true });
}

export async function DELETE() {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_SESSAO);
  return NextResponse.json({ ok: true });
}
