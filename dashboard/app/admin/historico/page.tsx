/**
 * /admin/historico — Histórico de execuções do worker.
 * INSTALAR NO SITE VERCEL: copiar para /app/admin/historico/page.tsx
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Execucao {
  id: number;
  iniciado_em: string;
  finalizado_em: string | null;
  fontes_verificadas: string[];
  novas_vagas: number;
  vagas_notificadas: number;
  erros: Record<string, string>;
  perfil_reconstruido: boolean;
}

export default function PaginaHistorico() {
  const [dados, setDados] = useState<{ itens: Execucao[]; total: number } | null>(null);
  const [pagina, setPagina] = useState(1);

  useEffect(() => {
    fetch(`/api/admin/proxy?path=/api/runs&pagina=${pagina}`)
      .then((r) => r.json())
      .then(setDados);
  }, [pagina]);

  function duracaoFormatada(inicio: string, fim: string | null) {
    if (!fim) return "—";
    const seg = Math.round(
      (new Date(fim).getTime() - new Date(inicio).getTime()) / 1000
    );
    return `${seg}s`;
  }

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Histórico de Execuções</h1>
        <Link href="/admin" className="text-sm text-blue-400 hover:text-blue-300">← Painel</Link>
      </div>

      {dados ? (
        <>
          <div className="space-y-3">
            {dados.itens.map((exec) => {
              const temErros = Object.keys(exec.erros).length > 0;
              return (
                <div
                  key={exec.id}
                  className={`bg-gray-900 border rounded-xl p-4 ${
                    temErros ? "border-red-800" : "border-gray-800"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-mono text-gray-300">
                        #{exec.id} — {new Date(exec.iniciado_em).toLocaleString("pt-BR")}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Fontes: {exec.fontes_verificadas.join(", ") || "—"} |{" "}
                        Duração: {duracaoFormatada(exec.iniciado_em, exec.finalizado_em)}
                      </p>
                    </div>
                    <div className="text-right text-sm">
                      <span className="text-green-400 font-medium">+{exec.novas_vagas} novas</span>
                      <span className="text-gray-400 mx-2">|</span>
                      <span className="text-blue-400">{exec.vagas_notificadas} alertas</span>
                    </div>
                  </div>

                  {exec.perfil_reconstruido && (
                    <span className="inline-block mt-2 text-xs bg-purple-900 text-purple-300 rounded px-2 py-0.5">
                      Perfil reconstruído
                    </span>
                  )}

                  {temErros && (
                    <div className="mt-2 text-xs text-red-400 bg-red-950 border border-red-800 rounded p-2">
                      Erros: {Object.entries(exec.erros).map(([k, v]) => `${k}: ${v}`).join(" | ")}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between mt-6 text-sm text-gray-400">
            <span>{dados.total} execuções no total</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPagina((p) => Math.max(1, p - 1))}
                disabled={pagina === 1}
                className="px-3 py-1 bg-gray-800 rounded disabled:opacity-40"
              >
                ←
              </button>
              <span className="px-3 py-1">Página {pagina}</span>
              <button
                onClick={() => setPagina((p) => p + 1)}
                disabled={pagina * 20 >= dados.total}
                className="px-3 py-1 bg-gray-800 rounded disabled:opacity-40"
              >
                →
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="text-center text-gray-500 py-20">Carregando histórico...</div>
      )}
    </main>
  );
}
