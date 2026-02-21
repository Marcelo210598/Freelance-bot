/**
 * /admin/config — Configurações do sistema.
 * INSTALAR NO SITE VERCEL: copiar para /app/admin/config/page.tsx
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Config {
  diaria_base: number;
  threshold_score: number;
  freq_minutos: number;
  github_refresh_horas: number;
  keywords_boost: string[];
  keywords_penalty: string[];
  pisos_por_categoria: Record<string, number>;
}

export default function PaginaConfig() {
  const [config, setConfig] = useState<Config | null>(null);
  const [editado, setEditado] = useState<Partial<Config>>({});
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState("");

  useEffect(() => {
    fetch("/api/admin/proxy?path=/api/settings")
      .then((r) => r.json())
      .then(setConfig);
  }, []);

  async function salvar() {
    setSalvando(true);
    setMensagem("");
    try {
      const resp = await fetch("/api/admin/proxy?path=/api/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editado),
      });
      const dados = await resp.json();
      setConfig(dados);
      setEditado({});
      setMensagem("Configurações salvas com sucesso!");
    } catch {
      setMensagem("Erro ao salvar. Tente novamente.");
    } finally {
      setSalvando(false);
    }
  }

  const val = <K extends keyof Config>(campo: K): Config[K] | undefined =>
    editado[campo] !== undefined ? editado[campo] : config?.[campo];

  if (!config) {
    return (
      <main className="min-h-screen bg-gray-950 text-white p-6">
        <p className="text-gray-400">Carregando configurações...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Configurações</h1>
        <Link href="/admin" className="text-sm text-blue-400 hover:text-blue-300">← Painel</Link>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* financeiro */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4">Financeiro</h2>
          <div className="space-y-4">
            <Campo
              label="Diária base (R$)"
              tipo="number"
              valor={String(val("diaria_base") ?? 100)}
              onChange={(v) => setEditado((e) => ({ ...e, diaria_base: Number(v) }))}
            />
            <Campo
              label="Score mínimo para alerta (0–1)"
              tipo="number"
              valor={String(val("threshold_score") ?? 0.45)}
              onChange={(v) => setEditado((e) => ({ ...e, threshold_score: Number(v) }))}
            />
          </div>
        </section>

        {/* scheduler */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4">Scheduler</h2>
          <div className="space-y-4">
            <Campo
              label="Frequência de coleta (minutos)"
              tipo="number"
              valor={String(val("freq_minutos") ?? 45)}
              onChange={(v) => setEditado((e) => ({ ...e, freq_minutos: Number(v) }))}
            />
            <Campo
              label="Refresh do GitHub (horas)"
              tipo="number"
              valor={String(val("github_refresh_horas") ?? 8)}
              onChange={(v) => setEditado((e) => ({ ...e, github_refresh_horas: Number(v) }))}
            />
          </div>
        </section>

        {/* pisos */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4">Pisos de valor por categoria</h2>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(config.pisos_por_categoria).map(([cat, piso]) => (
              <Campo
                key={cat}
                label={`${cat} (R$)`}
                tipo="number"
                valor={String(
                  (editado.pisos_por_categoria ?? config.pisos_por_categoria)[cat] ?? piso
                )}
                onChange={(v) =>
                  setEditado((e) => ({
                    ...e,
                    pisos_por_categoria: {
                      ...(e.pisos_por_categoria ?? config.pisos_por_categoria),
                      [cat]: Number(v),
                    },
                  }))
                }
              />
            ))}
          </div>
        </section>

        {mensagem && (
          <p className={`text-sm px-4 py-3 rounded-lg border ${
            mensagem.includes("sucesso")
              ? "text-green-400 bg-green-950 border-green-800"
              : "text-red-400 bg-red-950 border-red-800"
          }`}>
            {mensagem}
          </p>
        )}

        <button
          onClick={salvar}
          disabled={salvando || Object.keys(editado).length === 0}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-semibold rounded-xl py-3 transition-colors"
        >
          {salvando ? "Salvando..." : "Salvar Configurações"}
        </button>
      </div>
    </main>
  );
}

function Campo({
  label, tipo, valor, onChange,
}: {
  label: string;
  tipo: string;
  valor: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="block text-sm text-gray-400 mb-1">{label}</label>
      <input
        type={tipo}
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        step="any"
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}
