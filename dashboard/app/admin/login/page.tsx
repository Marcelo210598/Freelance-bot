/**
 * /admin/login — Tela de login simples por senha.
 * INSTALAR NO SITE VERCEL: copiar para /app/admin/login/page.tsx
 */

"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function PaginaLogin() {
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const router = useRouter();
  const params = useSearchParams();

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setCarregando(true);
    setErro("");

    try {
      const resp = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ senha }),
      });

      if (resp.ok) {
        const redirect = params.get("redirect") || "/admin";
        router.push(redirect);
      } else {
        const dados = await resp.json();
        setErro(dados.erro || "Senha incorreta.");
      }
    } catch {
      setErro("Erro de conexão. Tente novamente.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm bg-gray-900 rounded-2xl shadow-xl p-8 border border-gray-800">
        <h1 className="text-2xl font-bold text-white mb-2">Freelance Bot</h1>
        <p className="text-gray-400 text-sm mb-8">Painel administrativo</p>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1">Senha</label>
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {erro && (
            <p className="text-red-400 text-sm bg-red-950 border border-red-800 rounded-lg px-3 py-2">
              {erro}
            </p>
          )}

          <button
            type="submit"
            disabled={carregando}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg py-2.5 transition-colors"
          >
            {carregando ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
    </main>
  );
}
