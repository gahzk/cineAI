"""Busca por texto: a resposta do modelo é conferida contra as listas reais antes de virar busca."""
from types import SimpleNamespace

import pytest

from app import nl
from app.ranking import Filters


class FakeMessages:
    def __init__(self, parsed, stop_reason="end_turn"):
        self.parsed, self.stop_reason, self.kwargs = parsed, stop_reason, None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(parsed_output=self.parsed, stop_reason=self.stop_reason)


def use_fake(monkeypatch, parsed, stop_reason="end_turn"):
    messages = FakeMessages(parsed, stop_reason)
    monkeypatch.setattr(nl, "_client", SimpleNamespace(beta=SimpleNamespace(messages=messages)))
    return messages


def test_ids_inventados_sao_descartados(fake_tmdb, monkeypatch):
    use_fake(monkeypatch, Filters(genres=[80, 9999], exclude_genres=[1234], provider=777))
    f = nl.text_to_filters("crime")
    assert f.genres == [80] and f.exclude_genres == [] and f.provider is None


def test_pedido_vai_delimitado_e_com_listas(fake_tmdb, monkeypatch):
    messages = use_fake(monkeypatch, Filters())
    nl.text_to_filters("algo leve")
    content = messages.kwargs["messages"][0]["content"]
    assert "<pedido>algo leve</pedido>" in content and "Netflix" in content
    assert messages.kwargs["output_format"] is Filters


def test_recusa_vira_erro_claro(fake_tmdb, monkeypatch):
    use_fake(monkeypatch, None, stop_reason="refusal")
    with pytest.raises(nl.AIUnavailable):
        nl.text_to_filters("qualquer coisa")


class FakeOllama:
    def __init__(self, content=None, error=None):
        self.content, self.error, self.sent = content, error, None

    def __call__(self, url, json, timeout):
        self.sent = {"url": url, **json}
        if self.error:
            raise self.error
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"message": {"content": self.content}})


def use_ollama(monkeypatch, **kw):
    fake = FakeOllama(**kw)
    monkeypatch.setattr(nl, "OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setattr(nl.requests, "post", fake)
    return fake


def test_ollama_recebe_o_schema_e_ids_sao_conferidos(fake_tmdb, monkeypatch):
    fake = use_ollama(monkeypatch, content='{"genres": [80, 9999], "era": "classic"}')
    assert nl.enabled()
    f = nl.text_to_filters("um clássico de crime")
    assert f.genres == [80] and f.era == "classic"
    assert fake.sent["url"].endswith("/api/chat") and fake.sent["format"] == Filters.model_json_schema()
    assert "<pedido>um clássico de crime</pedido>" in fake.sent["messages"][1]["content"]


def test_ollama_resposta_fora_do_formulario_vira_erro_claro(fake_tmdb, monkeypatch):
    use_ollama(monkeypatch, content='{"era": "anos 90"}')
    with pytest.raises(nl.AIUnavailable):
        nl.text_to_filters("anos 90")


def test_ollama_desligado_avisa(fake_tmdb, monkeypatch):
    use_ollama(monkeypatch, error=nl.requests.ConnectionError())
    with pytest.raises(nl.AIUnavailable, match="Ollama não está rodando"):
        nl.text_to_filters("qualquer coisa")
