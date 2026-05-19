<div align="center">

# 🎬 cineAI

**An AI-powered cinematic recommendation engine, decoupled into a modern full-stack architecture for local-first development and production deployment.**

[![Status](https://img.shields.io/badge/status-active-success.svg)](https://github.com/gahzk/cineAI)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-React-61DAFB.svg?logo=react)](https://react.dev/)
[![Supabase](https://img.shields.io/badge/database-Supabase-3ECF8E.svg?logo=supabase)](https://supabase.com/)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg?logo=python)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-18%2B-339933.svg?logo=node.js)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-contributing)

[Quick Start](#-quick-start) • [Architecture](#-architecture-map) • [Features](#-feature-matrix) • [Troubleshooting](#-troubleshooting) • [Contributing](#-contributing)

</div>

---

## 📖 Overview

`cineAI` was originally a research notebook prototype. It has now been **fully migrated** into a production-ready, decoupled application composed of an independent Python/FastAPI **backend** serving the inference logic and a modern JavaScript **frontend** consuming it over a clean REST contract, with **Supabase** as the persistent data layer.

> **Migration Note:** Notebook-based execution has been deprecated. The system now runs as two long-lived services that can be developed, scaled, containerized, and deployed independently.

---

## 🗺️ Architecture Map

```text
┌─────────────────────────────────────────────────────────────────────┐
│                            USER (Browser)                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  HTTP / HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   /frontend  —  React  (Port 5173)                  │
│   ┌─────────────┐   ┌─────────────┐   ┌──────────────────────────┐  │
│   │  UI Layer   │ → │  API Client │ → │  State Mgmt (hooks/ctx)  │  │
│   └─────────────┘   └─────────────┘   └──────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  REST  (JSON over fetch/axios)
                                │  /api/v1/recommend, /api/v1/search
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  /backend  —  FastAPI  (Port 8000)                  │
│   ┌─────────────┐   ┌─────────────┐   ┌──────────────────────────┐  │
│   │  Routers    │ → │  Services   │ → │   AI / Inference Core    │  │
│   └─────────────┘   └─────────────┘   └────────────┬─────────────┘  │
└────────────────────────────────────────────────────┼────────────────┘
                                                     │
                                                     ▼
                              ┌─────────────────────────────────┐
                              │   /supabase  —  Persistence     │
                              │   (Auth · Postgres · Storage)   │
                              └─────────────────────────────────┘
```

**Communication contract:** strict JSON, versioned under `/api/v1/*`, CORS enabled for the frontend origin.

---

## 🚀 Quick Start

The project is split into independent services. Open **two terminals** — one per service.

### 🐍 1. Backend — `/backend`

<details open>
<summary><strong>Step-by-step setup</strong></summary>

```bash
# 1. Move into the backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows (PowerShell)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# then edit .env with your secrets

# 5. Launch the dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

</details>

#### `backend/.env`

| Variable           | Description                                | Example                       |
| ------------------ | ------------------------------------------ | ----------------------------- |
| `APP_ENV`          | Runtime environment                        | `development`                 |
| `API_PORT`         | Port the FastAPI server listens on         | `8000`                        |
| `MODEL_PATH`       | Local path to the AI model artifact        | `./models/cineai.bin`         |
| `TMDB_API_KEY`     | (Optional) Movie metadata provider key     | `xxxxxxxxxxxxxxxx`            |
| `SUPABASE_URL`     | Supabase project URL                       | `https://xxx.supabase.co`     |
| `SUPABASE_KEY`     | Supabase service/anon key                  | `eyJhbGciOi...`               |
| `CORS_ORIGINS`     | Comma-separated allowed origins            | `http://localhost:5173`       |
| `LOG_LEVEL`        | `debug` \| `info` \| `warning` \| `error`  | `info`                        |

> ✅ Once running, OpenAPI docs are auto-served at **`http://localhost:8000/docs`**.

---

### ⚛️ 2. Frontend — `/frontend`

<details open>
<summary><strong>Step-by-step setup</strong></summary>

```bash
# 1. Move into the frontend directory
cd frontend

# 2. Install dependencies
npm install            # or: pnpm install / yarn

# 3. Configure environment variables
cp .env.example .env.local
# then edit .env.local

# 4. Launch the dev server
npm run dev
```

</details>

#### `frontend/.env.local`

| Variable                  | Description                          | Example                        |
| ------------------------- | ------------------------------------ | ------------------------------ |
| `VITE_API_BASE_URL`       | Base URL of the backend API          | `http://localhost:8000/api/v1` |
| `VITE_SUPABASE_URL`       | Supabase project URL                 | `https://xxx.supabase.co`      |
| `VITE_SUPABASE_ANON_KEY`  | Supabase anonymous key               | `eyJhbGciOi...`                |
| `VITE_APP_NAME`           | Display name in the UI               | `cineAI`                       |

> ✅ The app boots at **`http://localhost:5173`** and talks to the backend over REST.

---

## ✅ Feature Matrix

| Capability                          | Legacy (Notebook)        | Current (Local Decoupled)               |
| ----------------------------------- | ------------------------ | --------------------------------------- |
| Persistent execution                | ❌ Session-bound         | ✅ Long-lived services                  |
| Public REST API                     | ❌ Not exposed           | ✅ Versioned `/api/v1/*`                |
| Modern UI                           | ❌ Notebook widgets only | ✅ React + responsive design            |
| Environment isolation               | ⚠️ Shared runtime        | ✅ `.venv` + isolated `node_modules`    |
| Configuration via `.env`            | ❌ Hardcoded             | ✅ Twelve-factor compliant              |
| Hot-reload dev experience           | ⚠️ Manual re-runs        | ✅ Uvicorn `--reload` + Vite HMR        |
| Type-safe contracts (OpenAPI)       | ❌                       | ✅ Auto-generated at `/docs`            |
| Persistent storage                  | ❌ In-memory only        | ✅ Supabase (Postgres + Auth)           |
| Independent scaling                 | ❌                       | ✅ Front and back deployable separately |
| Offline / on-prem ready             | ❌ Cloud-locked          | ✅ Fully local-first                    |

---

## 🧪 Health Check

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok","version":"1.0.0"}
```

<details>
<summary><strong>📜 Example startup logs</strong></summary>

```log
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     [cineAI] Loading model from ./models/cineai.bin ...
INFO:     [cineAI] Embeddings ready (dim=768, items=42_318)
INFO:     [cineAI] Supabase connection OK
INFO:     Application startup complete.
```

</details>

---

## 🛠️ Troubleshooting

<details>
<summary><strong>CORS errors in the browser console</strong></summary>

Ensure `CORS_ORIGINS` in `backend/.env` includes the exact frontend origin (scheme + host + port), e.g. `http://localhost:5173`. Restart the backend after any change.

</details>

<details>
<summary><strong>Port already in use (8000 / 5173)</strong></summary>

```bash
# Linux / macOS
lsof -i :8000 && kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Or override the port: `uvicorn app.main:app --port 8010`.

</details>

<details>
<summary><strong>Supabase connection fails</strong></summary>

Verify `SUPABASE_URL` and `SUPABASE_KEY` in `backend/.env`. Confirm the project is not paused in the Supabase dashboard, and that your network allows outbound HTTPS.

</details>

<details>
<summary><strong>Frontend cannot reach backend</strong></summary>

Confirm `VITE_API_BASE_URL` matches the backend host/port and that the backend is actually listening (`curl /health`).

</details>

---

## 🤝 Contributing

Contributions are welcome and appreciated.

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit using conventional commits: `feat:`, `fix:`, `docs:`, `refactor:` ...
4. Run linters/tests locally before pushing
5. Open a Pull Request describing **what** changed and **why**

A formal `CONTRIBUTING.md` will be added soon with full code style, branching strategy, and the review checklist.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for the full text.

---

<div align="center">

Built with care by [@gahzk](https://github.com/gahzk) and contributors.
<br/>
⭐ If this project helps you, consider starring the repo.

</div>
