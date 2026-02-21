/**
 * BFF (Backend-for-Frontend) — proxy para a Railway API.
 * Injeta X-ADMIN-TOKEN server-side (nunca exposto ao browser).
 *
 * Uso: GET/PATCH /api/admin/proxy?path=/api/stats
 *
 * INSTALAR NO SITE VERCEL: copiar para /app/api/admin/proxy/route.ts
 */

import { NextRequest, NextResponse } from "next/server";

const RAILWAY_URL = process.env.RAILWAY_API_URL!;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN!;

async function proxy(request: NextRequest, method: string) {
  const path = request.nextUrl.searchParams.get("path") || "/api/stats";
  const queryParams = new URLSearchParams(request.nextUrl.searchParams);
  queryParams.delete("path");

  const url = `${RAILWAY_URL}${path}${queryParams.size > 0 ? "?" + queryParams.toString() : ""}`;

  const opcoes: RequestInit = {
    method,
    headers: {
      "X-ADMIN-TOKEN": ADMIN_TOKEN,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  };

  if (method === "PATCH") {
    opcoes.body = await request.text();
  }

  try {
    const resposta = await fetch(url, opcoes);
    const dados = await resposta.json();
    return NextResponse.json(dados, { status: resposta.status });
  } catch (erro) {
    console.error("[BFF] Erro ao chamar Railway API:", erro);
    return NextResponse.json(
      { erro: "Falha ao comunicar com a API interna." },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest) {
  return proxy(request, "GET");
}

export async function PATCH(request: NextRequest) {
  return proxy(request, "PATCH");
}
