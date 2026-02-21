# DEVLOG — Freelance-bot

Registro de desenvolvimento. Atualizar a cada sessão.

---

## 2026-02-21 — Setup inicial completo

### O que foi implementado
- Estrutura completa do projeto criada em `/Desktop/Projetos AI/Freelance-bot/`
- **DB**: modelos SQLAlchemy (vagas, pontuacoes, candidaturas, perfil, configuracoes, execucoes)
- **Alembic**: migração inicial `001_initial.py`
- **API FastAPI**: endpoints /api/stats, /api/jobs, /api/settings, /api/runs + auth X-ADMIN-TOKEN
- **Worker**: APScheduler + ciclo completo (coleta → score → Telegram → histórico)
- **Coletores**: 99Freelas, Workana, Freelancer.com (API pública + fallback HTML)
- **Embeddings**: sentence-transformers all-MiniLM-L6-v2 (local, sem custo de API)
- **Scorer**: cosine similarity + boost/penalty por palavras-chave
- **Estimador**: heurísticas de complexidade + gerador de proposta em PT-BR
- **Telegram**: envio formatado Markdown, máx 5 por ciclo
- **Dashboard Next.js**: login, overview, vagas, config, histórico — BFF seguro
- **Testes**: test_coletores, test_dedupe, test_scoring + fixtures HTML/JSON
- **Docker**: Dockerfile.api, Dockerfile.worker, docker-compose.yml
- **Histórico**: registro de runs em history/YYYY-MM-DD/run_XXX.json

### Pendências
- [ ] Configurar `.env` com credenciais reais (Neon, Telegram, GitHub)
- [ ] Rodar `alembic upgrade head` para criar tabelas no Neon
- [ ] Deploy Railway: criar 2 serviços (API + Worker) com os Dockerfiles
- [ ] Integrar dashboard no site Vercel (copiar pasta `dashboard/`)
- [ ] Adicionar env vars no Vercel: ADMIN_PASSWORD, ADMIN_TOKEN, RAILWAY_API_URL
- [ ] Testar parsing das 3 fontes em produção (ajustar seletores CSS se mudarem)
- [ ] Página de detalhe da vaga `/admin/vagas/[id]` (opcional)

### Próxima ação sugerida
```
1. cd "Desktop/Projetos AI/Freelance-bot"
2. cp .env.example .env  → preencher variáveis
3. pip install -r requirements.txt
4. alembic upgrade head
5. uvicorn app.api.main:app --reload --port 8000
6. # Em outro terminal:
   python -m app.worker.main
```

### Comandos úteis
```bash
# Desenvolvimento local
uvicorn app.api.main:app --reload --port 8000
python -m app.worker.main

# Testes
pytest tests/ -v

# Docker (produção simulada)
docker compose up --build

# Migrações
alembic upgrade head
alembic revision --autogenerate -m "descricao"

# Ver logs do worker
python -m app.worker.main 2>&1 | tee history/worker.log
```

### Configuração Railway (deploy)
1. Criar projeto no Railway
2. Adicionar serviço → "Deploy from GitHub" → selecionar `Freelance-bot`
3. Para API: Build Command vazio, Start Command: `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
   - OU usar Dockerfile.api via "Custom Docker Build"
4. Para Worker: mesmo repo, Dockerfile.worker
5. Adicionar todas as env vars (DATABASE_URL, ADMIN_TOKEN, TELEGRAM_*, GITHUB_*)
6. URL da API (Railway) → salvar como RAILWAY_API_URL no Vercel

### Configuração Vercel (dashboard)
Copiar da pasta `dashboard/` para o seu site Next.js:
- `middleware.ts` → raiz do projeto
- `app/api/admin/login/route.ts` → criar pasta no seu app
- `app/api/admin/proxy/route.ts` → criar pasta no seu app
- `app/admin/` → todas as subpastas e arquivos

Env vars no Vercel:
```
ADMIN_PASSWORD=sua-senha-do-painel
ADMIN_TOKEN=mesmo-token-do-railway
RAILWAY_API_URL=https://seu-projeto.up.railway.app
NEXT_PUBLIC_BASE_URL=https://seusite.vercel.app
```
