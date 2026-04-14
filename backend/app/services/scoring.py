# -*- coding: utf-8 -*-
"""
Scoring engine — extracted and refactored from the CineAI legacy notebook.

Responsibilities:
- Genre/theme fuzzy matching (map_terms_to_genres)
- Duration scoring (get_duration_score)
- Main recommendation score (score_item)
- AI comment generation (generate_ai_comment)
"""
import random
from typing import Any, Dict, List, Optional

from rapidfuzz import fuzz, process

from app.core.utils import normalize, safe_float, safe_int

# ---------------------------------------------------------------------------
# Genre definitions
# ---------------------------------------------------------------------------

GEN_CANON: List[str] = [
    "Ação", "Aventura", "Animação", "Comédia", "Crime", "Documentário",
    "Drama", "Família", "Fantasia", "História", "Terror", "Música",
    "Mistério", "Romance", "Ficção Científica", "Cinema TV", "Thriller",
    "Guerra", "Faroeste",
]

# Theme → genre mapping (allows natural-language genre input)
THEMES: Dict[str, List[str]] = {
    "heist": ["Crime", "Ação"],
    "espacial": ["Ficção Científica", "Aventura"],
    "medieval": ["Fantasia", "História"],
    "super-heroi": ["Ação", "Aventura", "Fantasia"],
    "politica": ["Drama", "Thriller"],
    "biografia": ["Drama", "História"],
    "noir": ["Crime", "Mistério"],
    "musical": ["Música", "Romance"],
    "suspense": ["Thriller", "Mistério"],
    "acao": ["Ação"],
    "ficcao": ["Ficção Científica"],
    "ficção": ["Ficção Científica"],
    "sci-fi": ["Ficção Científica"],
    "terror": ["Terror"],
    "horror": ["Terror"],
    "comedia": ["Comédia"],
    "comedia romantica": ["Comédia", "Romance"],
    "documentario": ["Documentário"],
    "animacao": ["Animação"],
    "anime": ["Animação"],
}

_NORM_CANON = [normalize(g) for g in GEN_CANON]

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

TYPE_MATCH_BONUS = 60


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def map_terms_to_genres(terms: List[str]) -> List[str]:
    """
    Convert free-text genre/theme inputs into canonical genre names.
    Uses fuzzy matching against THEMES dict and GEN_CANON list.
    """
    from app.core.utils import is_empty
    out: set = set()
    for term in terms:
        if is_empty(term):
            continue
        nt = normalize(term)
        # Check theme dict first
        for tk, tg in THEMES.items():
            if fuzz.partial_ratio(nt, tk) > 85:
                out.update(tg)
        # Also try direct genre match
        best = process.extractOne(nt, _NORM_CANON, scorer=fuzz.token_set_ratio)
        if best and best[1] > 75:
            out.add(GEN_CANON[best[2]])
    return list(out)


def get_duration_score(pref: Optional[str], runtime: Optional[int]) -> float:
    """
    Return a 0..1 score indicating how well a title's runtime matches the user's preference.
    Returns 0.5 (neutral) when runtime or preference is unknown.
    """
    if runtime is None:
        return 0.5
    t = normalize(pref or "")
    if "curt" in t:   # Curta  → ~90 min
        return max(0.0, 1 - abs(runtime - 90) / 90)
    if "medi" in t:   # Média  → ~120 min
        return max(0.0, 1 - abs(runtime - 120) / 60)
    if "long" in t:   # Longa  → ~180 min
        return max(0.0, 1 - abs(runtime - 180) / 180)
    return 0.5


def score_item(item: Dict, prefs: Dict[str, Any]) -> float:
    """
    Core recommendation algorithm (ported 1:1 from the legacy notebook).

    Scoring breakdown:
    - +60   exact content-type match (movie vs tv)
    - +15   per included genre present in item
    - -25   per excluded genre present in item
    - +0..10 duration compatibility
    - +0..12 quality score  (vote_avg × vote_cnt density) × weight_rating
    - +0..12 popularity score × weight_popularity
    - ±year preference bonus/penalty
    """
    s = 0.0
    i_g_norm = normalize(item.get("genres", ""))

    # Type match
    if prefs.get("type") and prefs["type"] == item.get("type"):
        s += TYPE_MATCH_BONUS

    # Genre weights
    for g_norm in prefs.get("inc_norm", []):
        if g_norm in i_g_norm:
            s += 15
    for g_norm in prefs.get("exc_norm", []):
        if g_norm in i_g_norm:
            s -= 25

    # Duration
    s += 10 * get_duration_score(prefs.get("dur"), item.get("runtime"))

    # Quality & popularity
    va = safe_float(item.get("vote_avg"))
    vc = safe_int(item.get("vote_cnt"))
    pop = safe_float(item.get("popularity"))
    quality = (va / 10.0) * min(1.0, vc / 5000.0)
    popularity = min(1.0, pop / 1000.0)
    s += prefs.get("w_rating", 0.8) * quality * 12
    s += prefs.get("w_pop", 0.8) * popularity * 12

    # Year preference
    y = item.get("year") or 2000
    if prefs.get("classic_focus"):
        s += max(0, (2000 - y) / 10)
    elif prefs.get("prefer_new"):
        s += max(0, (y - 2000) / 3)
    else:
        s -= max(0, (y - 2010) / 4)

    return s


# ---------------------------------------------------------------------------
# AI Comment generation (local template engine, no LLM required)
# ---------------------------------------------------------------------------

_COMMENT_TEMPLATES: Dict[str, List[str]] = {
    "Ação": ["Adrenalina pura do início ao fim.", "Sequências de ação que prendem do começo ao fim."],
    "Aventura": ["Uma jornada épica que vale a experiência.", "Aventura inesquecível."],
    "Comédia": ["Gargalhadas garantidas em cada cena.", "Leveza e humor que aliviam qualquer dia."],
    "Drama": ["Uma história emocionante que toca a alma.", "Drama intenso com performances memoráveis."],
    "Ficção Científica": ["Expande a mente com conceitos fascinantes.", "Fica pensando muito tempo depois dos créditos."],
    "Terror": ["Deixa as luzes acesas — você foi avisado.", "Tensão crescente que não dá folga."],
    "Romance": ["Para aquecer o coração em qualquer dia.", "Química entre os personagens transbordante."],
    "Mistério": ["Um quebra-cabeça que te mantém na beira do sofá.", "Reviravoltas que ninguém prevê."],
    "Animação": ["Visualmente deslumbrante para todas as idades.", "Arte e história se fundem de forma perfeita."],
    "Thriller": ["Tensão do começo ao fim — impossível pausar.", "Suspense calculado com maestria."],
    "Crime": ["Mergulha fundo no submundo com estilo.", "Roteiro afiado e personagens complexos."],
    "Documentário": ["Perspectiva que muda a forma de ver o mundo.", "Revelações que ficam na memória."],
    "default": ["Merece uma chance — você não vai se arrepender.", "Título que surpreende positivamente."],
}

_QUALIFIER_PHRASES: Dict[str, List[str]] = {
    "acclaimed":  ["Aclamado pela crítica e pelo público.", "Um dos melhores do gênero."],
    "popular":    ["O fenômeno do momento que todo mundo comenta.", "Impossível não ter ouvido falar."],
    "underrated": ["Uma joia subestimada que poucos conhecem.", "Merece muito mais atenção do que recebe."],
    "classic":    ["Um verdadeiro clássico que resistiu ao tempo.", "Referência absoluta do cinema."],
}


def generate_ai_comment(item: Dict) -> str:
    """Generate a short editorial comment for a catalog item based on its metadata."""
    genres = item.get("genres", "").split("|")
    primary_genre = genres[0] if genres and genres[0] else "default"
    parts = [random.choice(_COMMENT_TEMPLATES.get(primary_genre, _COMMENT_TEMPLATES["default"]))]

    va = safe_float(item.get("vote_avg"))
    yr = item.get("year") or 2025
    pop = safe_float(item.get("popularity"))

    if va >= 8.2:
        parts.append(random.choice(_QUALIFIER_PHRASES["acclaimed"]))
    elif yr < 2000:
        parts.append(random.choice(_QUALIFIER_PHRASES["classic"]))
    elif pop > 1000:
        parts.append(random.choice(_QUALIFIER_PHRASES["popular"]))
    elif 6.8 <= va < 7.8:
        parts.append(random.choice(_QUALIFIER_PHRASES["underrated"]))

    return " ".join(parts)
