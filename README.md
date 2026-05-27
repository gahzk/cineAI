<div align="center">

# 🎬 CineAI

**Sistema Inteligente de Recomendação de Filmes e Séries**
_Busca Híbrida · Comentários Editoriais Locais · Arquitetura Full-Stack Desacoplada_

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![JavaScript](https://img.shields.io/badge/JavaScript-Vanilla-F7DF1E?logo=javascript&logoColor=black)](https://developer.mozilla.org/docs/Web/JavaScript)
[![TMDB](https://img.shields.io/badge/TMDB-API_v4-01B4E4?logo=themoviedatabase&logoColor=white)](https://www.themoviedb.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Plataforma de recomendação que combina um **catálogo local cacheado do TMDB**, **consultas em tempo real à API do TMDB** e **comentários editoriais gerados localmente** — servida através de uma API REST (FastAPI) e um frontend leve em HTML/CSS/JS.

</div>

---

## 📋 Sumário

- [Visão Geral](#-visão-geral)
- [Arquitetura](#-arquitetura)
- [Stack Tecnológica](#-stack-tecnológica)
- [Como Rodar](#-como-rodar)
- [Funcionalidades](#-funcionalidades)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Referência da API](#-referência-da-api)
- [Troubleshooting](#-troubleshooting)
- [Licença](#-licença)

---

## 🎯 Visão Geral

O **CineAI** é um motor de recomendação inteligente para filmes e séries. O sistema orquestra duas estratégias complementares:

- **Busca Rápida** — resultados instantâneos do catálogo local de mais de 1.300 títulos curados;
- **Busca Específica** — consultas em tempo real à API do TMDB com filtros avançados (ator, diretor, palavra-chave, ano, classificação).

Os resultados são apresentados em uma interface web simples, com autenticação JWT, página de populares da semana e dashboard analítico para administradores.

### Diferenciais

- **Algoritmo de scoring transparente** — cada peso é explicável (gênero, duração, qualidade, popularidade, época)
- **Comentários editoriais locais** — gerados a partir de templates, sem custo de LLM externo
- **Fuzzy matching** — tolerante a erros de digitação em gêneros/temas (via RapidFuzz)
- **Providers de streaming (BR)** — mostra em quais serviços cada título está disponível
- **Dashboard analítico** — métricas agregadas de uso para administradores

---

## 🏗 Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                  NAVEGADOR (Cliente)                    │
│  login.html · index.html · trending.html · dashboard    │
│              ↓ fetch() com JWT no header                │
└─────────────────────────────────────────────────────────┘
                          ↓ HTTP/HTTPS
┌─────────────────────────────────────────────────────────┐
│              SERVIDOR FastAPI (Uvicorn)                 │
│                                                         │
│  Routers:     auth → recommendations → analytics       │
│  Services:    tmdb.py → scoring.py → analytics.py      │
│  Models:      User → UserPreference → History          │
│                                                         │
│         ↓ SQLAlchemy async      ↓ requests              │
└─────────────────────────────────────────────────────────┘
       ↓                                ↓
  ┌─────────────┐                ┌──────────────────┐
  │   SQLite    │                │   TMDB API v4    │
  │ cineai.db   │                │ themoviedb.org   │
  └─────────────┘                └──────────────────┘
```

O servidor FastAPI entrega **tanto a API JSON quanto os arquivos HTML estáticos** na mesma porta (8000) — evitando problemas de CORS e simplificando o deploy.

---

## 🛠 Stack Tecnológica

| Camada       | Tecnologia                                  | Função                                              |
| ------------ | ------------------------------------------- | --------------------------------------------------- |
| **Backend**  | Python 3.11+ · FastAPI · Uvicorn            | API REST assíncrona                                 |
| **ORM**      | SQLAlchemy 2.0 (async) · aiosqlite          | Acesso ao banco com async/await                     |
| **Banco**    | SQLite (dev) · PostgreSQL/Supabase (prod)   | Armazenamento de usuários, preferências, histórico  |
| **Auth**     | python-jose · passlib · bcrypt              | JWT + hash de senhas                                |
| **Frontend** | HTML5 · CSS3 · JavaScript Vanilla · Chart.js | UI sem framework (zero build step)                  |
| **Fuzzy**    | RapidFuzz                                   | Match de gêneros e temas tolerante a erros          |
| **HTTP**     | requests                                    | Cliente TMDB com pool de conexões e retry           |
| **Validação**| Pydantic 2 · pydantic-settings              | Schemas de request/response e configuração via .env |

---

## 🚀 Como Rodar

> **Pré-requisito:** Obtenha um TMDB v4 Bearer Token grátis em [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).

### Backend

```bash
git clone https://github.com/gahzk/cineAI.git
cd cineAI/backend

# 1. Criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env e preencha TMDB_BEARER_TOKEN e SECRET_KEY

# 4. Rodar o servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Acesso

| URL                                  | Descrição                                  |
| ------------------------------------ | ------------------------------------------ |
| `http://localhost:8000`              | Interface principal (busca)                |
| `http://localhost:8000/login`        | Tela de login / cadastro                   |
| `http://localhost:8000/trending`     | Populares da semana                        |
| `http://localhost:8000/dashboard`    | Dashboard analítico (apenas admins)        |
| `http://localhost:8000/api/docs`     | Documentação interativa Swagger (OpenAPI)  |
| `http://localhost:8000/api/health`   | Health check                               |

O frontend é servido pelo próprio FastAPI a partir da pasta `/frontend` — **não há build step nem servidor separado**.

---

## ✅ Funcionalidades

- 🔐 **Autenticação JWT** — cadastro, login e sessões com tokens de 7 dias
- 🔒 **Senhas com bcrypt** — sal automático e fator de custo configurável
- 🎯 **Busca Rápida** — recomendação Top 3 ranqueada do catálogo local (~1.357 títulos)
- 🌐 **Busca Específica** — consulta em tempo real ao TMDB com filtros granulares (ator, diretor, ano, keyword, classificação BR)
- 🔥 **Populares da Semana** — trending semanal de filmes + séries do TMDB
- 📊 **Dashboard Analítico** — KPIs, gráficos de distribuição e insights gerados a partir do histórico real (acesso restrito a admins)
- 💾 **Persistência de preferências** — última configuração de busca é salva por usuário
- 📝 **Histórico de recomendações** — toda recomendação gerada é registrada
- 🤖 **Comentários editoriais** — gerados localmente via templates por gênero
- 🔍 **Fuzzy matching** — entrada "ficção", "sci-fi" e "Ficção Científica" são equivalentes

---

## 📁 Estrutura do Projeto

```
cineAI/
├── backend/
│   ├── app/
│   │   ├── main.py            # Entrypoint FastAPI + mount do frontend
│   │   ├── config.py          # Settings via Pydantic (carrega .env)
│   │   ├── database.py        # Engine async + get_db()
│   │   ├── core/
│   │   │   ├── security.py    # JWT + bcrypt
│   │   │   └── utils.py       # normalize(), helpers
│   │   ├── models/            # SQLAlchemy ORM (User, UserPreference, History)
│   │   ├── schemas/           # Pydantic (validação de request/response)
│   │   ├── routers/           # Endpoints HTTP (auth, recommendations, analytics)
│   │   └── services/          # tmdb.py, scoring.py, analytics.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── index.html             # Página principal (busca)
│   ├── login.html             # Login + cadastro
│   ├── trending.html          # Populares da semana
│   ├── dashboard.html         # Dashboard analítico
│   ├── css/style.css          # Estilos globais
│   └── js/
│       ├── api.js             # Cliente fetch() centralizado
│       ├── auth.js            # requireAuth(), initNavbar(), logout
│       ├── app.js             # Lógica da página de busca
│       └── dashboard.js       # Lógica do dashboard (Chart.js)
│
├── .github/                   # Templates de issue/PR e workflow de CI
├── LICENSE
└── README.md
```

---

## 🔌 Referência da API

Todos os endpoints da aplicação ficam sob o prefixo **`/api/v1`**.
Endpoints autenticados exigem o header `Authorization: Bearer <jwt>`.

| Método | Endpoint                                | Auth      | Descrição                                                 |
| ------ | --------------------------------------- | --------- | --------------------------------------------------------- |
| `POST` | `/api/v1/auth/register`                 | —         | Cadastra um novo usuário e retorna um token JWT           |
| `POST` | `/api/v1/auth/login`                    | —         | Autentica e retorna um token JWT                          |
| `GET`  | `/api/v1/auth/me`                       | JWT       | Retorna dados do usuário logado                           |
| `POST` | `/api/v1/recommendations/search`        | JWT       | Busca Rápida — Top 3 do catálogo local                    |
| `POST` | `/api/v1/recommendations/search/specific` | JWT     | Busca Específica — TMDB Discover com filtros avançados    |
| `GET`  | `/api/v1/recommendations/trending`      | JWT       | Filmes e séries em alta da semana                         |
| `GET`  | `/api/v1/recommendations/catalog/status`| —         | Status do catálogo local                                  |
| `GET`  | `/api/v1/analytics/summary`             | JWT (admin) | Métricas agregadas para o dashboard                     |
| `GET`  | `/api/health`                           | —         | Liveness probe                                            |
| `GET`  | `/api/health/db`                        | —         | Health check do banco                                     |

Documentação interativa Swagger disponível em **`/api/docs`** e ReDoc em **`/api/redoc`**.

---

## 🧰 Troubleshooting

<details>
<summary><strong>Backend falha ao iniciar — <code>TMDB_BEARER_TOKEN</code> não definido</strong></summary>

Certifique-se de que `backend/.env` existe e contém um token válido:

```env
TMDB_BEARER_TOKEN=eyJhbGciOi...
```
</details>

<details>
<summary><strong>Erro de CORS no console do navegador</strong></summary>

Confirme se `CORS_ORIGINS` no `backend/.env` inclui a origem do seu frontend (ou use `["*"]` em desenvolvimento). Lembre que `["*"]` é incompatível com `allow_credentials=True` — o projeto usa JWT no header `Authorization`, então isso não é problema.
</details>

<details>
<summary><strong>TMDB retorna 401 Unauthorized</strong></summary>

Seu token pode estar inválido ou expirado. Gere um novo **v4 Bearer Token** em [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).
</details>

<details>
<summary><strong>Catálogo local não carrega</strong></summary>

Na primeira execução, o serviço TMDB tenta baixar e cachear o catálogo. Verifique a conexão de rede e o token. O cache fica em `%TEMP%/cineai_cache/`.
</details>

<details>
<summary><strong>Erro <code>AttributeError: module 'bcrypt' has no attribute '__about__'</code></strong></summary>

Você instalou uma versão do `bcrypt` mais recente que `4.1`, que é incompatível com `passlib 1.7.4`. Force a versão correta:

```bash
pip install bcrypt==4.0.1
```
</details>

---

## 📜 Licença

Distribuído sob a **Licença MIT**. Veja [`LICENSE`](LICENSE) para o texto completo.

---

<div align="center">

Desenvolvido por **[Gabriel Oliveira Santos](https://github.com/gahzk)**

Se este projeto te ajudou, considere dar uma ⭐ no GitHub.

</div>
