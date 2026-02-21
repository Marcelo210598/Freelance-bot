/**
 * /admin/vagas — Lista de vagas com filtros e ações.
 * INSTALAR NO SITE VERCEL: copiar para /app/admin/vagas/page.tsx
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Vaga {
  id: number;
  fonte: string;
  titulo: string;
  url: string;
  orcamento_raw: string;
  score: number | null;
  complexity_score: number | null;
  valor_sugerido: number | null;
  status: string | null;
  criado_em: string;
}

interface Pagina {
  total: number;
  pagina: number;
  por_pagina: number;
  itens: Vaga[];
}

const STATUS_OPTIONS = [
  "todos",
  "encontrado",
  "candidatei",
  "em_conversa",
  "aceita",
  "recusada",
  "concluida",
];

const FONTE_OPTIONS = ["todos", "99freelas", "workana", "freelancer"];

export default function PaginaVagas() {
  const [dados, setDados] = useState<Pagina | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [status, setStatus] = useState("todos");
  const [fonte, setFonte] = useState("todos");
  const [minScore, setMinScore] = useState(0);
  const [busca, setBusca] = useState("");
  const [pagina, setPagina] = useState(1);

  async function buscarVagas() {
    setCarregando(true);
    const params = new URLSearchParams({
      path: "/api/jobs",
      pagina: String(pagina),
      por_pagina: "20",
      min_score: String(minScore),
    });
    if (status !== "todos") params.set("status", status);
    if (fonte !== "todos") params.set("fonte", fonte);
    if (busca) params.set("q", busca);

    try {
      const resp = await fetch(`/api/admin/proxy?${params}`);
      const json = await resp.json();
      setDados(json);
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    buscarVagas();
  }, [status, fonte, minScore, pagina]);

  async function atualizarStatus(vagaId: number, novoStatus: string) {
    await fetch(`/api/admin/proxy?path=/api/jobs/${vagaId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: novoStatus }),
    });
    buscarVagas();
  }

  const corScore = (score: number | null) => {
    if (!score) return "text-gray-500";
    if (score >= 0.7) return "text-green-400";
    if (score >= 0.5) return "text-yellow-400";
    return "text-red-400";
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Vagas</h1>
        <Link href="/admin" className="text-sm text-blue-400 hover:text-blue-300">← Painel</Link>
      </div>

      {/* filtros */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPagina(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s === "todos" ? "Todos os status" : s}</option>
          ))}
        </select>

        <select
          value={fonte}
          onChange={(e) => { setFonte(e.target.value); setPagina(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
        >
          {FONTE_OPTIONS.map((f) => (
            <option key={f} value={f}>{f === "todos" ? "Todas as fontes" : f}</option>
          ))}
        </select>

        <select
          value={minScore}
          onChange={(e) => { setMinScore(Number(e.target.value)); setPagina(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
        >
          <option value={0}>Qualquer score</option>
          <option value={0.4}>Score ≥ 40%</option>
          <option value={0.6}>Score ≥ 60%</option>
          <option value={0.75}>Score ≥ 75%</option>
        </select>

        <input
          type="text"
          placeholder="Buscar..."
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && buscarVagas()}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 flex-1 min-w-48"
        />
      </div>

      {/* tabela */}
      {carregando ? (
        <div className="text-center text-gray-500 py-20">Carregando...</div>
      ) : dados && dados.itens.length > 0 ? (
        <>
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400">
                  <th className="text-left px-4 py-3">Vaga</th>
                  <th className="text-left px-4 py-3">Fonte</th>
                  <th className="text-right px-4 py-3">Score</th>
                  <th className="text-right px-4 py-3">Valor Sugerido</th>
                  <th className="text-left px-4 py-3">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {dados.itens.map((vaga) => (
                  <tr key={vaga.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="px-4 py-3">
                      <a
                        href={vaga.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 font-medium line-clamp-1"
                      >
                        {vaga.titulo}
                      </a>
                      {vaga.orcamento_raw && (
                        <span className="text-gray-500 text-xs block">{vaga.orcamento_raw}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400 capitalize">{vaga.fonte}</td>
                    <td className={`px-4 py-3 text-right font-mono ${corScore(vaga.score)}`}>
                      {vaga.score != null ? `${(vaga.score * 100).toFixed(0)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-green-400">
                      {vaga.valor_sugerido
                        ? `R$ ${vaga.valor_sugerido.toLocaleString("pt-BR")}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={vaga.status || "encontrado"}
                        onChange={(e) => atualizarStatus(vaga.id, e.target.value)}
                        className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white"
                      >
                        {STATUS_OPTIONS.filter((s) => s !== "todos").map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/admin/vagas/${vaga.id}`}
                        className="text-xs text-blue-400 hover:text-blue-300"
                      >
                        Ver →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* paginação */}
          <div className="flex items-center justify-between mt-4 text-sm text-gray-400">
            <span>{dados.total} vagas encontradas</span>
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
                disabled={pagina * dados.por_pagina >= dados.total}
                className="px-3 py-1 bg-gray-800 rounded disabled:opacity-40"
              >
                →
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="text-center text-gray-500 py-20">Nenhuma vaga encontrada.</div>
      )}
    </main>
  );
}
