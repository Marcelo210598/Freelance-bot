/**
 * /admin — Overview com KPIs do dashboard.
 * INSTALAR NO SITE VERCEL: copiar para /app/admin/page.tsx
 */

import Link from "next/link";

async function obterStats() {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";
  const resp = await fetch(`${baseUrl}/api/admin/proxy?path=/api/stats`, {
    cache: "no-store",
  });
  if (!resp.ok) return null;
  return resp.json();
}

export default async function PaginaAdmin() {
  const stats = await obterStats();

  const kpis = stats
    ? [
        { label: "Total de Vagas", valor: stats.total_vagas, cor: "blue" },
        { label: "Novas Hoje", valor: stats.novas_hoje, cor: "green" },
        { label: "Candidaturas Ativas", valor: stats.candidaturas_ativas, cor: "yellow" },
        { label: "Aceitas", valor: stats.aceitas, cor: "purple" },
        { label: "Concluídas", valor: stats.concluidas, cor: "gray" },
        {
          label: "Score Médio",
          valor: `${(stats.score_medio * 100).toFixed(1)}%`,
          cor: "indigo",
        },
      ]
    : [];

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      {/* cabeçalho */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Freelance Bot</h1>
          <p className="text-gray-400 text-sm mt-1">Painel de controle</p>
        </div>
        <nav className="flex gap-4 text-sm">
          <Link href="/admin/vagas" className="text-blue-400 hover:text-blue-300">Vagas</Link>
          <Link href="/admin/config" className="text-blue-400 hover:text-blue-300">Config</Link>
          <Link href="/admin/historico" className="text-blue-400 hover:text-blue-300">Histórico</Link>
        </nav>
      </div>

      {/* KPIs */}
      {stats ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            {kpis.map((kpi) => (
              <div
                key={kpi.label}
                className="bg-gray-900 border border-gray-800 rounded-xl p-4"
              >
                <p className="text-gray-400 text-xs mb-1">{kpi.label}</p>
                <p className="text-2xl font-bold text-white">{kpi.valor}</p>
              </div>
            ))}
          </div>

          {/* por fonte */}
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-lg font-semibold mb-4">Por Fonte</h2>
              <ul className="space-y-2">
                {Object.entries(stats.por_fonte as Record<string, number>).map(([fonte, qtd]) => (
                  <li key={fonte} className="flex justify-between text-sm">
                    <span className="text-gray-300 capitalize">{fonte}</span>
                    <span className="font-medium">{qtd}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-lg font-semibold mb-4">Por Status</h2>
              <ul className="space-y-2">
                {Object.entries(stats.por_status as Record<string, number>).map(([status, qtd]) => (
                  <li key={status} className="flex justify-between text-sm">
                    <span className="text-gray-300 capitalize">{status.replace("_", " ")}</span>
                    <span className="font-medium">{qtd}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      ) : (
        <div className="text-center text-gray-500 py-20">
          <p className="text-lg">Não foi possível conectar à API.</p>
          <p className="text-sm mt-2">Verifique se o Railway API está rodando e as env vars estão corretas.</p>
        </div>
      )}
    </main>
  );
}
