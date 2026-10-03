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
