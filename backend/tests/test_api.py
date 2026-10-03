"""Fluxos pela API: conta, busca, histórico, admin e erros."""
import pytest
from sqlalchemy import update

from app import nl
from app.db import SessionLocal, User
from app.ranking import Filters
from tests.conftest import ANA


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_cadastro_login_e_me(client, token):
    me = client.get("/api/auth/me", headers=auth(token))
    assert me.status_code == 200 and me.json()["username"] == "ana"
    ok = client.post("/api/auth/login", json={"email": "ana@exemplo.com", "password": "senha-forte"})
    assert ok.status_code == 200
    errado = client.post("/api/auth/login", json={"email": "ana@exemplo.com", "password": "outra-senha"})
    assert errado.status_code == 401


def test_cadastro_rejeita_duplicado_e_senha_curta(client, token):
    dup = client.post("/api/auth/register", json={**ANA, "username": "outra"})
    assert dup.status_code == 400
    curta = client.post("/api/auth/register", json={"email": "b@exemplo.com", "username": "bia", "password": "123"})
    assert curta.status_code == 422


def test_login_bloqueia_apos_muitas_tentativas(client, token):
    for _ in range(10):
        client.post("/api/auth/login", json={"email": "ana@exemplo.com", "password": "errada-123"})
    r = client.post("/api/auth/login", json={"email": "ana@exemplo.com", "password": "senha-forte"})
    assert r.status_code == 429


def test_token_invalido_e_401(client):
    assert client.get("/api/auth/me", headers=auth("lixo")).status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_busca_e_populares_funcionam_sem_login(client):
    r = client.post("/api/search", json={"genres": [80]})
    assert r.status_code == 200 and len(r.json()["results"]) == 3
    assert client.get("/api/trending").status_code == 200
    assert client.get("/api/options").json()["text_search"] is False


def test_busca_logada_grava_historico(client, token):
    client.post("/api/search", json={"genres": [80]}, headers=auth(token))
    hist = client.get("/api/history", headers=auth(token)).json()["results"]
    assert len(hist) == 3
    # SQLite e MySQL devolvem a data sem fuso; a API marca como UTC para o navegador converter.
    assert hist[0]["recommended_at"].endswith(("Z", "+00:00"))


def test_filtro_invalido_e_422(client):
    assert client.post("/api/search", json={"content_type": "anime"}).status_code == 422
    assert client.post("/api/search", json={"min_vote": 50}).status_code == 422


def test_tmdb_fora_vira_503_com_mensagem(client, fake_tmdb):
    fake_tmdb.fail = True
    r = client.post("/api/search", json={})
    assert r.status_code == 503 and "TMDB" in r.json()["detail"]


def test_admin_exige_permissao(client, token):
    assert client.get("/api/admin/summary", headers=auth(token)).status_code == 403
    with SessionLocal() as db:
        db.execute(update(User).values(is_admin=True))
        db.commit()
    client.post("/api/search", json={"genres": [80]}, headers=auth(token))
    resumo = client.get("/api/admin/summary", headers=auth(token)).json()
    assert resumo["users"] == 1 and resumo["recommendations"] == 3
    assert resumo["top_genres"][0]["name"] in {"Crime", "Drama"}
    assert resumo["user_list"][0]["email"] == ANA["email"] and resumo["user_list"][0]["recommendations"] == 3
    assert len(resumo["recent"]) == 3 and resumo["recent"][0]["username"] == "ana"


def test_admin_email_cria_conta_e_promove(client, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "ADMIN_EMAIL", "dono@exemplo.com")
    monkeypatch.setattr(main, "ADMIN_PASSWORD", "senha-do-dono")
    main.ensure_admin()
    main.ensure_admin()  # rodar de novo não duplica
    r = client.post("/api/auth/login", json={"email": "dono@exemplo.com", "password": "senha-do-dono"})
    me = client.get("/api/auth/me", headers=auth(r.json()["access_token"])).json()
    assert me["is_admin"] and me["username"] == "dono"


def test_cadastro_com_admin_email_vira_admin(client, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "ADMIN_EMAIL", "ana@exemplo.com")
    r = client.post("/api/auth/register", json=ANA)
    assert client.get("/api/auth/me", headers=auth(r.json()["access_token"])).json()["is_admin"]


def test_busca_por_texto_desligada_sem_chave(client, token):
    r = client.post("/api/search/text", json={"text": "um suspense curto"}, headers=auth(token))
    assert r.status_code == 503


def test_busca_por_texto_usa_os_filtros_da_ia(client, token, monkeypatch):
    monkeypatch.setattr(nl, "text_to_filters", lambda text: Filters(genres=[80], era="classic"))
    r = client.post("/api/search/text", json={"text": "crime antigo"}, headers=auth(token))
    assert r.status_code == 200
    assert r.json()["filters"]["era"] == "classic"


def test_busca_por_texto_exige_login(client):
    assert client.post("/api/search/text", json={"text": "crime antigo"}).status_code == 401


def test_frontend_e_servido(client):
    assert client.get("/").status_code == 200
    assert client.get("/login.html").status_code == 200


@pytest.mark.parametrize("text", ["ab", "x" * 301])
def test_texto_tem_limites(client, token, text):
    assert client.post("/api/search/text", json={"text": text}, headers=auth(token)).status_code == 422
