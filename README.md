<div align="center">

# CineAI

### Recomendador Inteligente de Filmes e Séries

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TMDB API](https://img.shields.io/badge/TMDB_API-v4-01D277?style=for-the-badge&logo=themoviedatabase&logoColor=white)](https://www.themoviedb.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br>

**Sistema web de recomendação com busca dupla, autenticação JWT, banco de dados e painel de analytics.**

Evolução do MVP em Jupyter Notebook para uma aplicação web completa com backend em FastAPI e frontend em HTML/CSS/JS puro.

---

[Início Rápido](#-início-rápido) · [Funcionalidades](#-funcionalidades) · [Arquitetura](#-arquitetura) · [API](#-api-endpoints) · [Guia de Testes](GUIA_TESTES.md)

</div>

---

## Início Rápido

### Opção A — Download do pacote (recomendado)

> Não precisa clonar o repositório.

1. Vá em [**Releases**](../../releases) e baixe o arquivo `cineai-vX.X.X.zip`
2. Extraia o ZIP em qualquer pasta
3. Execute conforme seu sistema:

**Windows**
```
Dê duplo clique em start.bat
```

**Linux / macOS**
```bash
chmod +x start.sh && ./start.sh
```

4. Na primeira execução, cole seu **token TMDB** quando solicitado
5. O navegador abre automaticamente em `http://localhost:8000`

---

### Opção B — Clonar e rodar manualmente

```bash
# 1. Clonar
git clone https://github.com/gahzk/cineAI.git
cd cineAI

# 2. Instalar dependências
cd backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configurar ambiente
cp .env.example .env
# Edite .env e insira seu TMDB_BEARER_TOKEN

# 4. Subir servidor
uvicorn app.main:app --reload --port 8000
```

Acesse `http://localhost:8000`

---

### Token TMDB (gratuito)

| Passo | Ação |
|---|---|
| 1 | Crie conta em [themoviedb.org](https://www.themoviedb.org) |
| 2 | Acesse **Configurações → API** |
| 3 | Copie o **Bearer Token (v4 Auth)** |

---

## Funcionalidades

### Busca Dupla de Recomendações

| Modo | Como funciona | Velocidade |
|---|---|---|
| **Busca Rápida** | Pontua catálogo local de 2500+ títulos com o algoritmo `score_item` | Instantânea (após 1ª execução) |
| **Busca Específica** | Consulta ao vivo a API TMDB com filtros avançados | 3–8 segundos |

### Filtros Disponíveis

- Gêneros para incluir e excluir (com mapeamento fuzzy — escreve "espacial", encontra "Ficção Científica")
- Ator/atriz, diretor(a), produtora, streaming
- Ano de lançamento, nota mínima, classificação indicativa BR
- Duração ideal (Curta / Média / Longa), pesos de nota vs. popularidade

### Por resultado, o sistema exibe

Sinopse · Elenco · Diretor/Criador · Onde assistir no Brasil · Classificação BR · Temporadas (séries) · Títulos similares · Comentário gerado por IA local

### Gestão de Usuários

- Cadastro e login com JWT (token válido por 7 dias)
- Preferências salvas no banco por usuário
- Histórico completo de recomendações recebidas

### Dashboard de Analytics (Admin)

- Total de usuários e recomendações geradas
- Distribuição de gêneros (gráfico de barras)
- Modos de busca (Normal vs. Específica)
- Perfil de pesos dos usuários
- Top títulos mais recomendados
- Insights automáticos gerados dos dados

---

## Arquitetura

```
cineAI/
├── start.bat                   ← Launcher Windows (duplo clique)
├── start.sh                    ← Launcher Linux/Mac
├── scripts/
│   └── build_release.py        ← Empacota ZIP para distribuição
├── .github/
│   └── workflows/release.yml   ← GitHub Actions: publica release automaticamente
│
├── backend/
│   ├── app/
│   │   ├── main.py             ← FastAPI entry point + CORS + static serving
│   │   ├── config.py           ← pydantic-settings (.env)
│   │   ├── database.py         ← SQLAlchemy async (SQLite dev / PostgreSQL prod)
│   │   ├── core/
│   │   │   ├── utils.py        ← normalize, safe_float, get_year (do notebook)
│   │   │   └── security.py     ← JWT + bcrypt
│   │   ├── models/             ← User, UserPreference, RecommendationHistory
│   │   ├── schemas/            ← Pydantic (auth, prefs, recomendações, analytics)
│   │   ├── services/
│   │   │   ├── tmdb.py         ← Motor TMDB extraído do notebook
│   │   │   ├── scoring.py      ← score_item + map_terms_to_genres (do notebook)
│   │   │   └── analytics.py    ← Queries de agregação para o dashboard
│   │   └── routers/
│   │       ├── auth.py         ← /register /login /me
│   │       ├── recommendations.py  ← /search /search/specific /catalog/status
│   │       └── analytics.py    ← /analytics/summary (admin)
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── login.html              ← Login / Cadastro
    ├── index.html              ← Página de busca
    ├── dashboard.html          ← Painel admin (Chart.js)
    ├── css/style.css           ← Tema dark/neon-pink
    └── js/
        ├── api.js              ← Cliente HTTP com JWT
        ├── auth.js             ← requireAuth(), initNavbar()
        ├── app.js              ← Lógica de busca e renderização
        └── dashboard.js        ← Gráficos e tabelas
```

---

## API Endpoints

> Documentação interativa completa em `http://localhost:8000/api/docs`

### Autenticação

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Criar conta |
| `POST` | `/api/v1/auth/login` | Login → JWT |
| `GET` | `/api/v1/auth/me` | Dados do usuário logado |

### Recomendações

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/recommendations/catalog/status` | Status do catálogo local |
| `POST` | `/api/v1/recommendations/search` | Busca Rápida (catálogo) |
| `POST` | `/api/v1/recommendations/search/specific` | Busca Específica (API TMDB) |

### Analytics (admin)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/analytics/summary` | Dashboard completo |

### Sistema

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/health` | Health check |

---

## Stack Tecnológica

| Camada | Tecnologia | Versão |
|---|---|---|
| **Backend** | FastAPI + Uvicorn | 0.111 |
| **ORM** | SQLAlchemy (async) | 2.0 |
| **Banco (dev)** | SQLite + aiosqlite | — |
| **Banco (prod)** | PostgreSQL + asyncpg | — |
| **Auth** | python-jose + passlib/bcrypt | — |
| **NLP/Fuzzy** | RapidFuzz | 3.9 |
| **HTTP** | Requests + urllib3 | — |
| **Frontend** | HTML5 + CSS3 + JS (Vanilla) | — |
| **Charts** | Chart.js | 4.4 |
| **Dados** | TMDB API v4 | — |

---

## Publicando um Release

```bash
# 1. Gerar o ZIP manualmente
python scripts/build_release.py --version 2.1.0

# 2. Publicar via GitHub Actions (automático)
git tag v2.1.0
git push origin v2.1.0
# → Actions cria o Release com o ZIP em Releases
```

---

## Estrutura do .env

```env
TMDB_BEARER_TOKEN=seu_token_aqui          # obrigatório
DATABASE_URL=sqlite+aiosqlite:///./cineai.db
SECRET_KEY=gere-com-python-secrets        # mude em produção
ACCESS_TOKEN_EXPIRE_MINUTES=10080         # 7 dias
CATALOG_TARGET=2500
CACHE_EXPIRATION_DAYS=7
```

---

## Licença

Distribuído sob a [Licença MIT](LICENSE).

---

<div align="center">

Desenvolvido por [**Gabriel Oliveira Santos**](https://github.com/gahzk)

</div>
