<div align="center">

# 🎬 cineAI

**Sistema inteligente de recomendação de filmes e séries — arquitetura full-stack desacoplada, local-first e pronta para produção.**

[![Status](https://img.shields.io/badge/status-ativo-success.svg)](https://github.com/gahzk/cineAI)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-React-61DAFB.svg?logo=react)](https://react.dev/)
[![Supabase](https://img.shields.io/badge/database-Supabase-3ECF8E.svg?logo=supabase)](https://supabase.com/)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg?logo=python)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-18%2B-339933.svg?logo=node.js)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/licença-MIT-yellow.svg)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-bem--vindas-brightgreen.svg)](#-contribuindo)

### 🏠 [Página Principal do Projeto](https://github.com/gahzk/cineAI) · 📡 [API Docs](http://localhost:8000/docs) · 🖥️ [App Local](http://localhost:5173)

[Início Rápido](#-início-rápido) • [Arquitetura](#-arquitetura) • [Funcionalidades](#-funcionalidades) • [Solução de Problemas](#-solução-de-problemas) • [Contribuindo](#-contribuindo)

</div>

---

## 🏠 Página Principal

> A **página principal** do cineAI é servida pelo módulo `/frontend` (React + Vite) e consome a API exposta pelo `/backend` (FastAPI). Ao subir os dois serviços localmente, a interface fica disponível em **`http://localhost:5173`**.

| Recurso                | URL                                                   | Descrição                                          |
| ---------------------- | ----------------------------------------------------- | -------------------------------------------------- |
| 🖥️ App (local)         | [`localhost:5173`](http://localhost:5173)             | Interface principal: catálogo, busca e recomendações. |
| 📡 API (local)         | [`localhost:8000/api/v1`](http://localhost:8000/api/v1) | Endpoints REST versionados.                        |
| 📘 OpenAPI / Swagger   | [`localhost:8000/docs`](http://localhost:8000/docs)   | Documentação interativa auto-gerada.               |
| 🗄️ Repositório         | [`github.com/gahzk/cineAI`](https://github.com/gahzk/cineAI) | Código-fonte e issues.                             |
| 🌐 Deploy (produção)   | _<!-- adicionar URL aqui quando publicado -->_         | Em breve.                                          |

<!--
  📸 Screenshot da tela principal — substitua o link abaixo por uma imagem real:
  ![Página principal do cineAI](./docs/screenshot-home.png)
-->

> Quer ver rodando? Siga o [Início Rápido](#-início-rápido) — em poucos minutos a página principal estará no ar na sua máquina.

---

## 📖 Visão Geral

O **cineAI** começou como um protótipo em notebook de pesquisa. Foi **totalmente migrado** para uma aplicação desacoplada e pronta para produção, composta por:

- 🐍 **`/backend`** — API em Python/FastAPI com a lógica de inferência e recomendação.
- ⚛️ **`/frontend`** — Interface em React/Vite que entrega a página principal ao usuário.
- 🟢 **`/supabase`** — Camada de persistência (Postgres + Auth + Storage).

> **Nota de migração:** a execução via notebook foi descontinuada. O sistema agora roda como serviços de longa duração, independentes, containerizáveis e implantáveis separadamente.

---

## 🗺️ Arquitetura

```text
┌─────────────────────────────────────────────────────────────────────┐
│                       USUÁRIO  (Navegador)                          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  HTTP / HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│         /frontend  —  React + Vite  (Página Principal · 5173)       │
│   ┌─────────────┐   ┌─────────────┐   ┌──────────────────────────┐  │
│   │  UI / Pages │ → │  API Client │ → │   Estado (hooks/ctx)     │  │
│   └─────────────┘   └─────────────┘   └──────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  REST (JSON)
                                │  /api/v1/recommend, /api/v1/search
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                /backend  —  FastAPI  (API · 8000)                   │
│   ┌─────────────┐   ┌─────────────┐   ┌──────────────────────────┐  │
│   │   Routers   │ → │  Services   │ → │   Núcleo de IA / Modelo  │  │
│   └─────────────┘   └─────────────┘   └────────────┬─────────────┘  │
└────────────────────────────────────────────────────┼────────────────┘
                                                     │
                                                     ▼
                              ┌─────────────────────────────────┐
                              │   /supabase  —  Persistência    │
                              │   (Auth · Postgres · Storage)   │
                              └─────────────────────────────────┘
```

**Contrato de comunicação:** JSON estrito, versionado em `/api/v1/*`, com CORS liberado para a origem do frontend.

---

## 🚀 Início Rápido

O projeto é dividido em serviços independentes. Abra **dois terminais** — um para cada serviço.

### 🐍 1. Backend — `/backend`

<details open>
<summary><strong>Passo a passo</strong></summary>

```bash
# 1. Entre na pasta do backend
cd backend

# 2. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows (PowerShell)

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# em seguida, edite o .env com seus segredos

# 5. Suba o servidor de desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

</details>

#### `backend/.env`

| Variável           | Descrição                                  | Exemplo                       |
| ------------------ | ------------------------------------------ | ----------------------------- |
| `APP_ENV`          | Ambiente de execução                       | `development`                 |
| `API_PORT`         | Porta de escuta do FastAPI                 | `8000`                        |
| `MODEL_PATH`       | Caminho local do artefato do modelo de IA  | `./models/cineai.bin`         |
| `TMDB_API_KEY`     | (Opcional) Chave do provedor de metadados  | `xxxxxxxxxxxxxxxx`            |
| `SUPABASE_URL`     | URL do projeto Supabase                    | `https://xxx.supabase.co`     |
| `SUPABASE_KEY`     | Chave service/anon do Supabase             | `eyJhbGciOi...`               |
| `CORS_ORIGINS`     | Origens permitidas (separadas por vírgula) | `http://localhost:5173`       |
| `LOG_LEVEL`        | `debug` \| `info` \| `warning` \| `error`  | `info`                        |

> ✅ Após subir, a documentação OpenAPI fica em **`http://localhost:8000/docs`**.

---

### ⚛️ 2. Frontend — `/frontend`

<details open>
<summary><strong>Passo a passo</strong></summary>

```bash
# 1. Entre na pasta do frontend
cd frontend

# 2. Instale as dependências
npm install            # ou: pnpm install / yarn

# 3. Configure as variáveis de ambiente
cp .env.example .env.local
# em seguida, edite o .env.local

# 4. Suba o servidor de desenvolvimento
npm run dev
```

</details>

#### `frontend/.env.local`

| Variável                  | Descrição                            | Exemplo                        |
| ------------------------- | ------------------------------------ | ------------------------------ |
| `VITE_API_BASE_URL`       | URL base da API do backend           | `http://localhost:8000/api/v1` |
| `VITE_SUPABASE_URL`       | URL do projeto Supabase              | `https://xxx.supabase.co`      |
| `VITE_SUPABASE_ANON_KEY`  | Chave anônima do Supabase            | `eyJhbGciOi...`                |
| `VITE_APP_NAME`           | Nome exibido na UI                   | `cineAI`                       |

> ✅ A **página principal** sobe em **`http://localhost:5173`** e conversa com o backend via REST.

---

## ✨ Funcionalidades

| Capacidade                                | Legado (Notebook)        | Atual (Local Desacoplado)                |
| ----------------------------------------- | ------------------------ | ---------------------------------------- |
| Execução persistente                      | ❌ Limitada à sessão     | ✅ Serviços de longa duração             |
| API REST pública                          | ❌ Não exposta           | ✅ Versionada em `/api/v1/*`             |
| Interface moderna                         | ❌ Apenas widgets        | ✅ React + design responsivo             |
| Página principal acessível via navegador  | ❌                       | ✅ `http://localhost:5173`               |
| Isolamento de ambiente                    | ⚠️ Runtime compartilhado | ✅ `.venv` + `node_modules` isolados     |
| Configuração via `.env`                   | ❌ Hardcoded             | ✅ Twelve-factor                         |
| Hot-reload no desenvolvimento             | ⚠️ Re-runs manuais       | ✅ Uvicorn `--reload` + Vite HMR         |
| Contratos type-safe (OpenAPI)             | ❌                       | ✅ Auto-gerados em `/docs`               |
| Persistência                              | ❌ Apenas em memória     | ✅ Supabase (Postgres + Auth)            |
| Escalonamento independente                | ❌                       | ✅ Front e back deployáveis separadamente |
| Offline / on-prem                         | ❌ Travado em nuvem      | ✅ 100% local-first                      |

---

## 🧪 Verificação de Saúde

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok","version":"1.0.0"}
```

<details>
<summary><strong>📜 Exemplo de logs de inicialização</strong></summary>

```log
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     [cineAI] Carregando modelo de ./models/cineai.bin ...
INFO:     [cineAI] Embeddings prontos (dim=768, items=42_318)
INFO:     [cineAI] Conexão Supabase OK
INFO:     Application startup complete.
```

</details>

---

## 🛠️ Solução de Problemas

<details>
<summary><strong>Erros de CORS no console do navegador</strong></summary>

Garanta que `CORS_ORIGINS` em `backend/.env` inclui a origem exata do frontend (esquema + host + porta), por exemplo `http://localhost:5173`. Reinicie o backend após qualquer alteração.

</details>

<details>
<summary><strong>Porta já em uso (8000 / 5173)</strong></summary>

```bash
# Linux / macOS
lsof -i :8000 && kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Ou troque a porta: `uvicorn app.main:app --port 8010`.

</details>

<details>
<summary><strong>Falha ao conectar no Supabase</strong></summary>

Verifique `SUPABASE_URL` e `SUPABASE_KEY` em `backend/.env`. Confirme se o projeto não está pausado no dashboard do Supabase e se a rede permite saída HTTPS.

</details>

<details>
<summary><strong>Frontend não acessa o backend</strong></summary>

Confirme que `VITE_API_BASE_URL` aponta para o host/porta corretos e que o backend está mesmo escutando (`curl /health`).

</details>

---

## 🤝 Contribuindo

Contribuições são muito bem-vindas!

1. Faça um fork do repositório
2. Crie uma branch de feature: `git checkout -b feat/sua-feature`
3. Use commits convencionais: `feat:`, `fix:`, `docs:`, `refactor:` ...
4. Rode linters e testes localmente antes de enviar
5. Abra um Pull Request descrevendo **o que** mudou e **por quê**

Um `CONTRIBUTING.md` formal será adicionado em breve com o estilo de código, estratégia de branches e checklist de revisão.

---

## 📄 Licença

Distribuído sob a **Licença MIT**. Veja [`LICENSE`](./LICENSE) para o texto completo.

---

<div align="center">

Feito com 🎬 por [@gahzk](https://github.com/gahzk) e colaboradores.
<br/>
⭐ Se este projeto te ajuda, considere dar uma estrela no repositório.

</div>
