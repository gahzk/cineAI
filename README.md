# CineAI

Recomenda 3 filmes ou séries a partir dos filtros que você escolhe e explica por que escolheu cada um.
Os dados vêm ao vivo do [TMDB](https://www.themoviedb.org/). Com uma IA ligada (de graça, pelo [Ollama](https://ollama.com/) no seu computador), dá para descrever o que você quer em texto livre ("um suspense curto dos anos 90") e o modelo traduz o pedido em filtros.

Backend em Python (FastAPI + SQLAlchemy + SQLite). Frontend em HTML, CSS e JavaScript puro, servido pelo próprio backend.

## Como rodar

No Windows, o jeito mais fácil é dar dois cliques em `iniciar.bat` (veja `COMO-RODAR.txt`). Manualmente:

Precisa de Python 3.11+ e de um token de leitura (v4) do TMDB.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # preencha TMDB_TOKEN e SECRET_KEY
uvicorn app.main:app --reload --env-file .env
```

Abra http://localhost:8000. A documentação da API fica em http://localhost:8000/api/docs.

## Usar MySQL em vez de SQLite

Crie o banco e um usuário no seu MySQL (8.x) ou MariaDB:

```sql
CREATE DATABASE cineai CHARACTER SET utf8mb4;
CREATE USER 'cineai'@'localhost' IDENTIFIED BY 'troque-esta-senha';
GRANT ALL ON cineai.* TO 'cineai'@'localhost';
```

No `backend/.env`, aponte para ele:

```
DATABASE_URL=mysql+pymysql://cineai:troque-esta-senha@localhost:3306/cineai?charset=utf8mb4
```

As tabelas são criadas sozinhas na primeira vez que o servidor sobe. Se a senha tiver `@`, `:` ou `/`, troque por `%40`, `%3A` e `%2F` na URL.
Para abrir o site em outros aparelhos da sua rede, rode `uvicorn app.main:app --host 0.0.0.0 --env-file .env` e acesse `http://IP-do-computador:8000` (o Firewall do Windows vai pedir permissão).

## Como a recomendação funciona

1. Os filtros viram uma consulta ao `/discover` do TMDB, para filmes e séries (gêneros pedidos com OU; ator, diretor, duração e classificação só existem para filmes).
2. Cada candidato recebe uma nota:

| Parcela | Pontos |
|---|---|
| Cada gênero pedido que o título tem | 15 |
| Qualidade: nota/10 × min(1, votos/5000) | até 12 × peso da nota |
| Popularidade: min(1, popularidade/300) | até 12 × peso da popularidade |
| Época "clássicos" ou "recentes" | bônus pela distância do ano de corte |

Pesos por ordenação (nota, popularidade): equilibrado (0,8; 0,8), mais bem avaliados (1,0; 0,3), mais populares (0,3; 1,0).

3. Os 3 primeiros ganham detalhes (elenco, onde assistir no Brasil, trailer) e a lista "Por que recomendamos", montada a partir das mesmas parcelas.

A busca por texto faz uma única chamada a um modelo de linguagem, que devolve os filtros; o resto é igual. Sem IA configurada, esse campo fica desligado.

## Ligar a busca por texto (grátis, com Ollama)

1. Instale o [Ollama](https://ollama.com/download) e deixe-o aberto.
2. Baixe um modelo pequeno: `ollama pull qwen3:4b`
3. No `backend/.env`, adicione `OLLAMA_MODEL=qwen3:4b` e reinicie o servidor.

A resposta do modelo é forçada a seguir o formato do formulário e os gêneros e serviços são conferidos contra as listas do TMDB, então um modelo pequeno não consegue inventar filmes. Em computador sem placa de vídeo, cada pedido pode levar alguns segundos.
Também funciona com o Claude (pago): use `ANTHROPIC_API_KEY` no lugar de `OLLAMA_MODEL`.

## Testes

```bash
cd backend
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

Os testes usam um TMDB falso e não precisam de internet nem de tokens. O CI roda lint, testes e `pip-audit` em todo PR.

## Administrador

A página `/admin.html` mostra os usuários cadastrados, as últimas recomendações e os gêneros e títulos mais recomendados. Para ter acesso, coloque no `backend/.env`:

```
ADMIN_EMAIL=voce@exemplo.com
ADMIN_PASSWORD=uma-senha-forte
```

Ao subir, o servidor cria essa conta (se ainda não existir) e a marca como admin. O `iniciar.bat` pergunta esses dados na primeira vez.

Para abrir o banco diretamente: o SQLite fica em `backend/cineai.db` e abre no [DB Browser for SQLite](https://sqlitebrowser.org/) (grátis); no MySQL, use o MySQL Workbench.

## Limitações

- O histórico só é salvo para quem está logado.
- O limite de tentativas de login fica em memória: reinicia com o servidor e não vale para vários processos.
- O cache das respostas do TMDB também fica em memória.
- Se você tinha um `cineai.db` da versão anterior, contas e senhas continuam valendo; as tabelas antigas de preferências e catálogo deixam de ser usadas e podem ser apagadas junto com o arquivo, se quiser começar do zero.

## Licença

[MIT](LICENSE)
