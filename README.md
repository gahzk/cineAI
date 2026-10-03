# CineAI

Recomenda 3 filmes ou séries a partir dos filtros que você escolhe e explica por que escolheu cada um.
Os dados vêm ao vivo do [TMDB](https://www.themoviedb.org/). Com uma chave da Anthropic, dá para descrever o que você quer em texto livre ("um suspense curto dos anos 90") e o Claude traduz o pedido em filtros.

Backend em Python (FastAPI + SQLAlchemy + SQLite). Frontend em HTML, CSS e JavaScript puro, servido pelo próprio backend.

## Como rodar

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

A busca por texto faz uma única chamada ao Claude, que devolve os filtros; o resto é igual. Sem `ANTHROPIC_API_KEY`, esse campo fica desligado.

## Testes

```bash
cd backend
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

Os testes usam um TMDB falso e não precisam de internet nem de tokens. O CI roda lint, testes e `pip-audit` em todo PR.

## Administrador

A página `/admin.html` mostra contagens de uso. Para tornar uma conta admin:

```bash
cd backend
python -c "import sqlite3; c=sqlite3.connect('cineai.db'); c.execute(\"update users set is_admin=1 where email='voce@exemplo.com'\"); c.commit()"
```

## Limitações

- O histórico só é salvo para quem está logado.
- O limite de tentativas de login fica em memória: reinicia com o servidor e não vale para vários processos.
- O cache das respostas do TMDB também fica em memória.
- Se você tinha um `cineai.db` da versão anterior, contas e senhas continuam valendo; as tabelas antigas de preferências e catálogo deixam de ser usadas e podem ser apagadas junto com o arquivo, se quiser começar do zero.

## Licença

[MIT](LICENSE)
