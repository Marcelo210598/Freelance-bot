/**
 * Middleware Next.js — protege /admin/* e /api/admin/*
 * Verifica cookie de sessão antes de permitir acesso.
 *
 * INSTALAR NO SITE VERCEL: copiar para /middleware.ts (raiz do projeto Next.js)
 */

import { NextRequest, NextResponse } from "next/server";

const ROTAS_PROTEGIDAS = ["/admin", "/api/admin"];
const COOKIE_SESSAO = "freelance_bot_sessao";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const ehRotaProtegida = ROTAS_PROTEGIDAS.some((rota) =>
    pathname.startsWith(rota)
  );

  if (!ehRotaProtegida) {
    return NextResponse.next();
  }

  // permite acesso à página de login sem cookie
  if (pathname === "/admin/login") {
    return NextResponse.next();
  }

  // permite acesso ao endpoint de login
  if (pathname === "/api/admin/login") {
    return NextResponse.next();
  }

  const cookie = request.cookies.get(COOKIE_SESSAO);
  if (!cookie?.value) {
    const urlLogin = new URL("/admin/login", request.url);
    urlLogin.searchParams.set("redirect", pathname);
    return NextResponse.redirect(urlLogin);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/api/admin/:path*"],
};
