# Freelance-bot 🤖

Sistema 24/7 de rastreamento de vagas freelance com match inteligente, alertas Telegram e painel web no Vercel.

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    VERCEL (site)                         │
│  /admin → Next.js App Router                            │
│  /api/admin/* → BFF (injeta X-ADMIN-TOKEN server-side)  │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS (X-ADMIN-TOKEN)
┌──────────────────────────▼──────────────────────────────┐
│                  RAILWAY (Docker)                        │
│  ┌───────────────┐    ┌──────────────────────────────┐  │
│  │  API (FastAPI)│    │    Worker (APScheduler)       │  │
│  │  :8000        │    │  - coleta a cada 45min        │  │
│  └───────┬───────┘    │  - embeddings locais          │  │
│          │            │  - Telegram alerts            │  │
│          └────────────┤  - salva history/             │  │
└───────────────────────┼──────────────────────────────-┘
                        │ asyncpg (SSL)
┌───────────────────────▼──────────────────────────────-─┐
│               NEON PostgreSQL                           │
│  vagas | pontuacoes | candidaturas | perfil             │
│  configuracoes | execucoes                              │
└─────────────────────────────────────────────────────────┘
```

## Setup Local

### 1. Pré-requisitos
- Python 3.11+
- Node.js 18+ (para o dashboard)

### 2. Clonar e configurar

```bash
git clone https://github.com/Marcelo210598/Freelance-bot.git
cd Freelance-bot

# copiar e editar variáveis de ambiente
cp .env.example .env
# editar .env com suas credenciais reais
```

### 3. Instalar dependências Python

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Criar tabelas no banco

```bash
alembic upgrade head
```

### 5. Rodar localmente

**Terminal 1 — API:**
```bash
uvicorn app.api.main:app --reload --port 8000
# Acesse: http://localhost:8000/docs (só em dev)
```

**Terminal 2 — Worker:**
```bash
python -m app.worker.main
```

### 6. Testar

```bash
pytest tests/ -v
```

---

## Deploy Railway (Backend)

### Serviço 1: API

1. Criar novo projeto no Railway
2. "Deploy from GitHub" → selecionar repositório
3. Adicionar variáveis de ambiente (todas do `.env.example`)
4. Settings → Build:
   - Dockerfile Path: `Dockerfile.api`
5. Settings → Deploy:
   - Start Command: *(vazio — já definido no Dockerfile)*
6. Anotar a URL gerada (ex: `https://freelance-bot-api.up.railway.app`)

### Serviço 2: Worker

1. No mesmo projeto Railway, "Add Service" → mesmo repo
2. Settings → Build:
   - Dockerfile Path: `Dockerfile.worker`
3. Mesmas variáveis de ambiente

> ⚠️ Ambos os serviços precisam das mesmas env vars (especialmente `DATABASE_URL`).

---

## Deploy Vercel (Dashboard)

### 1. Copiar arquivos para o seu site Next.js

```bash
# No diretório raiz do seu site Vercel:
cp -r /caminho/Freelance-bot/dashboard/app/admin ./app/admin
cp -r /caminho/Freelance-bot/dashboard/app/api/admin ./app/api/admin
cp /caminho/Freelance-bot/dashboard/middleware.ts ./middleware.ts
```

> ⚠️ Se já existe um `middleware.ts` no seu site, **mescle** o conteúdo — não substitua.

### 2. Variáveis de ambiente no Vercel

No painel do Vercel → Settings → Environment Variables:

```
ADMIN_PASSWORD=sua-senha-forte-aqui
ADMIN_TOKEN=mesmo-valor-que-ADMIN_TOKEN-no-railway
RAILWAY_API_URL=https://freelance-bot-api.up.railway.app
NEXT_PUBLIC_BASE_URL=https://seusite.vercel.app
```

### 3. Deploy

```bash
git add . && git commit -m "feat: adiciona painel freelance-bot /admin"
git push  # Vercel faz deploy automático
```

### 4. Acessar

```
https://seusite.vercel.app/admin/login
```

---

## Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|---|---|---|
| `DATABASE_URL` | URL Neon PostgreSQL (asyncpg) | ✅ |
| `ADMIN_TOKEN` | Token Railway ↔ Vercel | ✅ |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram | ✅ |
| `TELEGRAM_CHAT_ID` | Chat ID para alertas | ✅ |
| `GITHUB_USERNAME` | Seu usuário GitHub | ✅ |
| `GITHUB_TOKEN` | Token GitHub (rate limit) | Recomendado |
| `PROFILE_URL` | URL pública do perfil JSON | Opcional |
| `DIARIA_BASE` | Diária base em R$ (default: 100) | Opcional |
| `THRESHOLD_SCORE` | Score mínimo para alerta (default: 0.45) | Opcional |
| `FREQ_MINUTOS` | Frequência de coleta (default: 45) | Opcional |
| `ADMIN_PASSWORD` | Senha do painel (Vercel) | ✅ (Vercel) |
| `RAILWAY_API_URL` | URL da API no Railway (Vercel) | ✅ (Vercel) |

---

## Estrutura do Projeto

```
Freelance-bot/
├── app/
│   ├── api/              # FastAPI (serviço 1)
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── middleware.py
│   │   └── routes/       # jobs, stats, settings, runs
│   ├── coletores/        # scrapers das 3 fontes
│   │   ├── base.py
│   │   ├── noventa_freelas.py
│   │   ├── workana.py
│   │   └── freelancer.py
│   ├── core/             # config, database, models
│   ├── perfil/           # GitHub builder + embeddings
│   ├── scoring/          # matcher + estimador
│   ├── notificacao/      # Telegram
│   ├── historico/        # registro de runs + DEVLOG
│   └── worker/           # scheduler + ciclo (serviço 2)
├── alembic/              # migrações de banco
├── dashboard/            # arquivos para copiar ao site Vercel
│   ├── middleware.ts
│   └── app/
│       ├── admin/        # páginas: login, overview, vagas, config, histórico
│       └── api/admin/    # BFF: login, proxy
├── tests/
│   ├── fixtures/         # HTML e JSON de teste
│   ├── test_coletores.py
│   ├── test_dedupe.py
│   └── test_scoring.py
├── history/
│   └── DEVLOG.md         # diário de desenvolvimento
├── Dockerfile.api
├── Dockerfile.worker
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── profile_override.json  # perfil curado (editar com seus dados)
```

---

## Perfil Curado (`profile_override.json`)

Edite o arquivo `profile_override.json` com suas habilidades e projetos:

```json
{
  "resumo": "Desenvolvedor full-stack...",
  "habilidades": ["Python", "Next.js", ...],
  "areas": ["APIs", "Automação", ...],
  "projetos_destaque": ["Projeto A", ...]
}
```

Alternativamente, publique uma URL em `/api/profile.json` no seu site Vercel e configure `PROFILE_URL`.

---

## Como funciona o ciclo

```
A cada 45 minutos:
1. Checa se GitHub mudou (pushed_at)
   └─ Se mudou → reconstrói perfil + embedding
2. Coleta vagas de 3 fontes (99Freelas, Workana, Freelancer)
3. Deduplica por (fonte, external_id)
4. Calcula score = 70% cosine similarity + 30% keywords
5. Estima complexidade, dias e valor sugerido
6. Gera sugestão de proposta em PT-BR
7. Envia top 5 vagas acima do threshold para o Telegram
8. Salva run_XXX.json em history/YYYY-MM-DD/
9. Registra execução no banco
```

---

## FAQ

**Q: Posso mudar a diária base sem reiniciar o worker?**
Sim — altere pelo painel `/admin/config`. O worker lê do banco a cada ciclo.

**Q: O bot envia candidaturas automaticamente?**
Não. Só rastreia, faz match e sugere. Você candidata manualmente.

**Q: E se um site mudar o HTML e o scraper parar?**
O log registrará o erro. O sistema tem fallback para seletores genéricos. Se necessário, atualize os seletores em `app/coletores/`.

**Q: O modelo de embeddings precisa de GPU?**
Não. `all-MiniLM-L6-v2` roda em CPU sem problemas. É leve e rápido.
