# Configurando Supabase como banco do CineAI

O backend do CineAI usa SQLAlchemy async. Para usar Supabase, conecte o app ao Postgres do Supabase pela variavel `DATABASE_URL`.

## 1. Pegue a connection string correta

No painel do Supabase:

1. Abra o projeto.
2. Clique em `Connect`.
3. Use uma destas opcoes:
   - `Session pooler`: recomendado para rodar localmente ou em redes sem IPv6.
   - `Direct connection`: recomendado para servidores persistentes com IPv6.

Use a string de Postgres. Nao use a URL do projeto, como `https://<project-ref>.supabase.co`.

## 2. Configure o `.env`

Crie `backend/.env` a partir de `backend/.env.example`:

```bash
cd backend
cp .env.example .env
```

No Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Preencha:

```env
TMDB_BEARER_TOKEN="seu-token-v4-do-tmdb"
DATABASE_URL=postgresql+asyncpg://postgres.<project-ref>:<database-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?ssl=require
SECRET_KEY=troque-por-um-segredo-forte
```

Se o Supabase entregar a string comecando com `postgres://` ou `postgresql://`, o backend tambem converte automaticamente para `postgresql+asyncpg://`. Deixar explicito no `.env` evita ambiguidade.

## 3. Suba o backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Na primeira inicializacao, o backend cria estas tabelas no Supabase:

- `users`
- `user_preferences`
- `recommendation_history`

## 4. Teste a conexao

Abra:

```text
http://localhost:8000/api/health/db
```

Resposta esperada:

```json
{
  "status": "ok",
  "database": "postgresql",
  "driver": "asyncpg"
}
```

## Observacoes

- Se aparecer erro dizendo que `DATABASE_URL` nao pode ser `https://...supabase.co`, copie a connection string do painel `Connect`; essa URL HTTP e usada pelas APIs do Supabase, nao pelo SQLAlchemy.
- Para apps FastAPI persistentes, prefira `Session pooler` ou `Direct connection`. O `Transaction pooler` na porta `6543` nao suporta prepared statements; o backend tenta desativar cache de prepared statements quando detecta essa porta, mas session/direct e o caminho mais estavel.
- O `.env` esta protegido pelo `.gitignore`. Mantenha tokens e senhas somente nele.
