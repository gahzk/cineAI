# CineAI v2 — Guia de Instalação, Uso e Testes

> Stack: **FastAPI (Python)** · **SQLite** · **HTML/CSS/JS** · **TMDB API**

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Instalação](#2-instalação)
3. [Subindo o servidor](#3-subindo-o-servidor)
4. [Interface Web — Passo a passo](#4-interface-web--passo-a-passo)
5. [Testando via API Docs (Swagger)](#5-testando-via-api-docs-swagger)
6. [Testando via curl](#6-testando-via-curl)
7. [Promovendo usuário a Admin](#7-promovendo-usuário-a-admin)
8. [Testando o Dashboard Analytics](#8-testando-o-dashboard-analytics)
9. [Checklist de funcionalidades](#9-checklist-de-funcionalidades)
10. [Problemas comuns](#10-problemas-comuns)

---

## 1. Pré-requisitos

| Ferramenta | Versão mínima | Verificar |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| pip | qualquer | `pip3 --version` |
| Navegador moderno | Chrome / Firefox / Edge | — |

> Nenhum Docker, Node.js ou banco externo é necessário para rodar em desenvolvimento.

---

## 2. Instalação

```bash
# 1. Entre na pasta do backend
cd cineAI/backend

# 2. Crie e ative um ambiente virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt
```

Confirme que o arquivo `.env` existe em `backend/.env`:

```bash
cat .env
# Deve mostrar TMDB_BEARER_TOKEN=eyJhbG...
```

Se não existir, crie-o copiando o exemplo:

```bash
cp .env.example .env
# Edite e preencha TMDB_BEARER_TOKEN com seu token
```

---

## 3. Subindo o servidor

```bash
# Dentro de cineAI/backend/ com o venv ativado
uvicorn app.main:app --reload --port 8000
```

Saída esperada:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

O banco de dados (`cineai.db`) é criado automaticamente na primeira execução.

Acesse:

| URL | O que é |
|---|---|
| `http://localhost:8000` | Aplicação Web (frontend) |
| `http://localhost:8000/login` | Página de login/cadastro |
| `http://localhost:8000/api/docs` | Swagger UI interativo |
| `http://localhost:8000/api/redoc` | Documentação Redoc |
| `http://localhost:8000/api/health` | Health check da API |

---

## 4. Interface Web — Passo a passo

### 4.1 Criar conta

1. Acesse `http://localhost:8000/login`
2. Clique na aba **"Criar conta"**
3. Preencha:
   - **Nome de usuário:** `cinefilo` (mín. 3 caracteres)
   - **E-mail:** `cinefilo@teste.com`
   - **Senha:** `123456` (mín. 6 caracteres)
4. Clique em **"Criar conta"**
5. Você será redirecionado automaticamente para a página principal

### 4.2 Busca Rápida (Catálogo Local)

> Na primeira execução esta busca constrói o catálogo de ~2500 títulos via TMDB.
> Pode levar **2–5 minutos**. As buscas seguintes são instantâneas (cache).

1. Na página principal, a aba **"Busca Rápida"** já está selecionada
2. Configure suas preferências:
   - **Formato:** clique em `Filme`, `Série` ou `Tanto faz`
   - **Gêneros que curte:** digite `ação, crime` (vírgulas separam)
   - **Gêneros para evitar:** `romance`
   - **Duração ideal:** `Média`
   - **Peso Nota / Popularidade:** ajuste os sliders
   - **Preferência de época:** `Recentes (pós 2010)`
3. Clique em **"Buscar recomendações"**
4. Aguarde o spinner — os **Top 3** aparecerão em cards com:
   - Sinopse, elenco, diretor
   - Onde assistir no Brasil
   - Classificação indicativa
   - Score de compatibilidade
   - Comentário gerado pela IA local

### 4.3 Busca Específica (API ao vivo)

1. Clique na aba **"Busca Específica"**
2. Preencha os filtros avançados — exemplos:
   - **Palavra-chave:** `heist`
   - **Ator:** `Brad Pitt`
   - **Diretor:** `David Fincher`
   - **Streaming:** `Netflix`
   - **Nota mínima:** `7.5`
3. Clique em **"Buscar na API"**
4. A busca consulta o TMDB em tempo real (3–8 segundos)

### 4.4 Fazer login novamente

1. Acesse `http://localhost:8000/login`
2. Use a aba **"Entrar"**
3. E-mail + senha cadastrados anteriormente

### 4.5 Sair

- Clique no botão **"Sair"** no canto superior direito da navbar

---

## 5. Testando via API Docs (Swagger)

Acesse `http://localhost:8000/api/docs` — interface interativa completa.

### 5.1 Registrar usuário

1. Expanda **`POST /api/v1/auth/register`**
2. Clique em **"Try it out"**
3. Cole no body:
```json
{
  "email": "teste@cineai.com",
  "username": "tester",
  "password": "senha123"
}
```
4. Execute — copie o `access_token` da resposta

### 5.2 Autenticar no Swagger

1. Clique no botão **"Authorize"** (cadeado) no topo da página
2. No campo `HTTPBearer (http, Bearer)` cole o token: `eyJhbG...`
3. Clique em **"Authorize"** → **"Close"**

### 5.3 Verificar usuário logado

1. Expanda **`GET /api/v1/auth/me`**
2. Execute — deve retornar seus dados

### 5.4 Status do catálogo

1. Expanda **`GET /api/v1/recommendations/catalog/status`**
2. Execute — mostra se o cache está válido e quantos títulos há

### 5.5 Busca Normal

1. Expanda **`POST /api/v1/recommendations/search`**
2. Cole:
```json
{
  "content_type": "movie",
  "genres_include": ["ação", "crime"],
  "genres_exclude": [],
  "duration_pref": "Média",
  "weight_rating": 1.0,
  "weight_popularity": 0.4,
  "prefer_new": true,
  "classic_focus": false,
  "save_preference": true
}
```
3. Execute — retorna Top 3 filmes pontuados

### 5.6 Busca Específica

1. Expanda **`POST /api/v1/recommendations/search/specific`**
2. Cole:
```json
{
  "content_type": "movie",
  "genres_include": ["thriller"],
  "genres_exclude": [],
  "weight_rating": 0.9,
  "weight_popularity": 0.5,
  "director": "Christopher Nolan",
  "min_vote": 8.0,
  "save_preference": true
}
```
3. Execute — busca direta na API TMDB

---

## 6. Testando via curl

> Substitua `SEU_TOKEN` pelo `access_token` obtido no registro/login.

### Health check
```bash
curl http://localhost:8000/api/health
```

### Registrar
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@cineai.com","username":"devuser","password":"dev123"}' | python3 -m json.tool
```

### Login
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@cineai.com","password":"dev123"}' | python3 -m json.tool
```

### Status do catálogo
```bash
curl -s http://localhost:8000/api/v1/recommendations/catalog/status \
  -H "Authorization: Bearer SEU_TOKEN" | python3 -m json.tool
```

### Busca Normal — filmes de ficção científica
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations/search \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "movie",
    "genres_include": ["ficção científica", "aventura"],
    "genres_exclude": ["terror"],
    "duration_pref": "Longa",
    "weight_rating": 1.0,
    "weight_popularity": 0.6,
    "prefer_new": false,
    "classic_focus": false,
    "save_preference": true
  }' | python3 -m json.tool
```

### Busca Específica — séries da HBO
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations/search/specific \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "tv",
    "genres_include": ["drama"],
    "genres_exclude": [],
    "weight_rating": 0.9,
    "weight_popularity": 0.5,
    "network": "HBO",
    "min_vote": 8.0,
    "save_preference": true
  }' | python3 -m json.tool
```

---

## 7. Promovendo usuário a Admin

O Dashboard de Analytics é restrito a admins. Para promover seu usuário:

```bash
# Dentro de cineAI/backend/
python3 -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select, update

async def promote(email):
    async with AsyncSessionLocal() as db:
        await db.execute(update(User).where(User.email == email).values(is_admin=True))
        await db.commit()
        print(f'Usuário {email} promovido a admin.')

asyncio.run(promote('SEU_EMAIL_AQUI'))
"
```

Substitua `SEU_EMAIL_AQUI` pelo e-mail cadastrado. Depois **faça logout e login novamente** para que o token seja atualizado.

Após a promoção, o link **"Dashboard"** aparecerá na navbar.

---

## 8. Testando o Dashboard Analytics

> Requer pelo menos uma busca realizada (para gerar dados no histórico).

### Via Interface

1. Faça login com o usuário admin
2. Clique em **"Dashboard"** na navbar
3. O painel carregará automaticamente com:
   - **KPIs:** total de usuários, recomendações geradas, gênero mais popular
   - **Gráfico de barras:** distribuição de gêneros
   - **Gráfico de rosca:** modos de busca (Normal vs. Específica)
   - **Gráfico horizontal:** perfil de pesos dos usuários
   - **Tabela de gêneros** com barra de progresso
   - **Tabela de títulos** mais recomendados
   - **Insights** gerados automaticamente pelos dados

### Via curl (admin)
```bash
curl -s http://localhost:8000/api/v1/analytics/summary \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN" | python3 -m json.tool
```

---

## 9. Checklist de funcionalidades

Execute cada item e confirme o resultado esperado:

| # | Teste | Resultado esperado |
|---|---|---|
| 1 | `GET /api/health` | `{"status":"ok","version":"2.0.0"}` |
| 2 | Registrar novo usuário | Token JWT retornado, redirect para `/` |
| 3 | Login com credenciais erradas | HTTP 401, mensagem "Credenciais inválidas" |
| 4 | Acessar `/` sem token | Redirect para `/login` |
| 5 | `GET /api/v1/auth/me` com token válido | Dados do usuário |
| 6 | Status do catálogo (1ª vez) | `cache_valid: false` |
| 7 | Busca Normal (1ª vez) | Demora 2–5 min, retorna 3 itens com detalhes |
| 8 | Busca Normal (2ª vez) | Resultado instantâneo (cache) |
| 9 | Busca Específica com filtros | Resultados diretos da API TMDB |
| 10 | Analytics sem ser admin | HTTP 403 Forbidden |
| 11 | Analytics com admin | JSON com gêneros, títulos, insights |
| 12 | Dashboard visual | Gráficos e tabelas carregados |
| 13 | Logout | Redirect para `/login`, token removido |

---

## 10. Problemas comuns

### `ModuleNotFoundError: No module named 'app'`
Execute sempre de dentro da pasta `backend/`:
```bash
cd cineAI/backend
uvicorn app.main:app --reload --port 8000
```

### `TMDB_BEARER_TOKEN não configurado`
Verifique se o arquivo `.env` existe em `backend/.env` e contém o token.

### Primeiro catálogo muito lento
Normal — o sistema faz ~200 requisições paralelas ao TMDB na primeira execução.
O catálogo fica em cache por 7 dias. Monitore o progresso nos logs do servidor.

### Porta 8000 já em uso
```bash
uvicorn app.main:app --reload --port 8001
```
Acesse em `http://localhost:8001`.

### Erro 422 no Swagger
Verifique se o body JSON está correto — todos os campos obrigatórios preenchidos.

### Dashboard em branco / sem dados
Faça pelo menos **1 busca** como usuário logado antes de acessar o dashboard.
O histórico de recomendações alimenta os gráficos.
