"""O algoritmo: parâmetros do Discover, nota e motivos. Os bugs da versão anterior viraram testes."""
from app import ranking, tmdb
from app.ranking import Filters
from tests.conftest import raw


def item(**kw):
    return tmdb.to_item(raw(**kw), "movie", {18: "Drama", 80: "Crime", 28: "Ação"})


def test_generos_pedidos_usam_ou_e_nao_e(fake_tmdb):
    p = ranking.discover_params("movie", Filters(genres=[28, 18]))
    assert p["with_genres"] == "28|18"


def test_genero_de_filme_vira_genero_de_serie(fake_tmdb):
    p = ranking.discover_params("tv", Filters(genres=[28, 18]))
    assert p["with_genres"] == "10759|18"


def test_tipo_sem_nenhum_genero_pedido_fica_de_fora(fake_tmdb):
    # Terror (27) não existe em séries no TMDB.
    assert ranking.discover_params("tv", Filters(genres=[27])) is None


def test_duracao_filtra_filmes(fake_tmdb):
    assert ranking.discover_params("movie", Filters(duration="short"))["with_runtime.lte"] == 100
    assert ranking.discover_params("movie", Filters(duration="long"))["with_runtime.gte"] == 140
    assert "with_runtime.gte" not in ranking.discover_params("movie", Filters())


def test_epoca_e_ano(fake_tmdb):
    assert ranking.discover_params("movie", Filters(era="classic"))["primary_release_date.lte"] == "1999-12-31"
    assert ranking.discover_params("tv", Filters(era="new"))["first_air_date.gte"] == "2010-01-01"
    p = ranking.discover_params("movie", Filters(era="new", year=1994))
    assert p["primary_release_year"] == 1994 and "primary_release_date.gte" not in p


def test_ator_restringe_a_filmes(fake_tmdb):
    f = Filters(actor="Fernanda Montenegro")
    assert ranking.kinds_for(f) == ["movie"]
    assert ranking.discover_params("movie", f)["with_cast"] == 500


def test_genero_pedido_sobe_a_nota(fake_tmdb):
    f = Filters(genres=[80])
    com = ranking.score(item(id_=1, title="A", genre_ids=[80]), f)
    sem = ranking.score(item(id_=2, title="B", genre_ids=[18]), f)
    assert com - sem == ranking.GENRE_POINTS


def test_ordenar_por_nota_favorece_aclamado(fake_tmdb):
    aclamado = item(id_=1, title="A", genre_ids=[], vote=9.0, votes=10000, pop=10)
    popular = item(id_=2, title="B", genre_ids=[], vote=6.0, votes=500, pop=300)
    por_nota = Filters(order="rating")
    por_pop = Filters(order="popularity")
    assert ranking.score(aclamado, por_nota) > ranking.score(popular, por_nota)
    assert ranking.score(popular, por_pop) > ranking.score(aclamado, por_pop)


def test_motivos_explicam_a_escolha(fake_tmdb):
    it = item(id_=1, title="A", genre_ids=[80], vote=8.6, votes=20000, pop=150, date="1974-01-01")
    it["providers"] = ["Netflix"]
    motivos = ranking.reasons(it, Filters(genres=[80], era="classic"))
    assert "Tem o que você pediu: Crime." in motivos
    assert any("nota 8.6 com 20.000 votos" in m for m in motivos)
    assert "Clássico de 1974." in motivos
    assert "Disponível em Netflix." in motivos


def test_recommend_devolve_top3_com_detalhes(fake_tmdb):
    results, total = ranking.recommend(Filters(genres=[80]))
    assert total == 5  # 4 filmes + 1 série
    assert len(results) == 3
    assert {r["title"] for r in results} >= {"Crime Aclamado", "Série de Crime"}
    assert all(r["reasons"] and r["providers"] == ["Netflix"] for r in results)
    assert results[0]["score"] >= results[1]["score"] >= results[2]["score"]


def test_discover_junta_varias_paginas_sem_repetir(fake_tmdb, monkeypatch):
    def paged(path, **params):
        fake_tmdb.calls.append((path, params))
        if path.startswith("/genre/"):
            return {"genres": [{"id": 80, "name": "Crime"}]}
        n = params["page"]
        page = [raw(id_=n * 100 + i, title=f"F{n}-{i}", genre_ids=[80]) for i in range(20)]
        return {"total_pages": 50, "results": page + [raw(id_=1, title="Repetido", genre_ids=[80])]}

    monkeypatch.setattr(tmdb, "get", paged)
    items = tmdb.discover("movie", {"sort_by": "popularity.desc"})
    pages = sorted(p["page"] for path, p in fake_tmdb.calls if path == "/discover/movie")
    assert pages == list(range(1, tmdb.DISCOVER_PAGES + 1))
    assert len(items) == tmdb.DISCOVER_PAGES * 20 + 1
    tmdb.discover("movie", {"sort_by": "popularity.desc"})  # segunda vez vem do cache
    assert len([c for c in fake_tmdb.calls if c[0] == "/discover/movie"]) == tmdb.DISCOVER_PAGES


def test_streamings_em_ordem_alfabetica_sem_acento(fake_tmdb, monkeypatch):
    def prov(path, **params):
        return {"results": [{"provider_id": i, "provider_name": n} for i, n in
                            enumerate(["Netflix", "amazon Prime Video", "Ápple TV", "Globoplay"])]}

    monkeypatch.setattr(tmdb, "get", prov)
    assert [p["name"] for p in tmdb.providers()] == ["amazon Prime Video", "Ápple TV", "Globoplay", "Netflix"]
