# -*- coding: utf-8 -*-

import sys, subprocess, time, re, unicodedata, random, json, os, argparse
from collections import deque
import concurrent.futures as cf
from typing import Any, Dict, List, Optional

# --- Dependências e Instalação ---
def _pip_install(p):
    """Verifica se a biblioteca está instalada e, se não estiver, a instala via pip."""
    try: __import__(p.split("==")[0])
    except ImportError: subprocess.check_call([sys.executable, "-m", "pip", "install", p, "-q"])

for dep in ["requests", "rapidfuzz", "rich"]: _pip_install(dep)

import requests
from rapidfuzz import fuzz, process
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.style import Style
from rich.box import ROUNDED, MINIMAL
from rich.theme import Theme as RichTheme

# --- Configurações Globais e Tema de Design ---
CINEAI_THEME = RichTheme({
    "primary": "#FF007F",
    "secondary": "#00B29A",
    "background": "#1a000d",
    "text": "white",
    "info": "grey70",
    "prompt": "cyan",
    "title": "bold #FF007F",
    "subtitle": "bold #00B29A",
    "success": "bold #00D26A",
    "warning": "bold #FFD700",
    "error": "bold #FF4F4F",
    "highlight": "bold #FF007F on #4D0026",
    "dim": "grey50"
})
console = Console(theme=CINEAI_THEME)

# Chave Bearer da API TMDB
TMDB_BEARER = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJkZTA0YjkwNjExM2ZlMWJiNTZiZjYzMWRiYmNjNmUzZiIsIm5iZiI6MTc1ODU5NDA2OS40NzgwMDAyLCJzdWIiOiI2OGQyMDQxNTM2ZWE2OTEzNzBjZDgwY2QiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.Z0dMqssuvDrfBsjIIkl4U0OE7npl5gSD7pAavmO6NyM"
BASE_URL = "https://api.themoviedb.org/3"
SESSION = requests.Session()
SESSION.headers.update({"Authorization": f"Bearer {TMDB_BEARER}", "Accept": "application/json"})

CACHE_DIR = "."; GENRES_CACHE_FILE = os.path.join(CACHE_DIR, "genres.json"); CATALOG_CACHE_FILE = os.path.join(CACHE_DIR, "catalog.json"); CACHE_EXPIRATION_DAYS = 7

# --- Funções de Lógica (Sem alterações) ---
def _norm(s: str) -> str:
    if s is None: return ""
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)).lower() if not unicodedata.combining(c)).strip()

def _tmdb_request(path, params=None, retries=3):
    wait_time = 0.25
    for _ in range(retries + 1):
        try:
            r = SESSION.get(f"{BASE_URL}{path}", params=params or {}, timeout=20);
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", wait_time)));
                wait_time = min(3.0, wait_time * 1.8);
                continue
            r.raise_for_status();
            return r.json()
        except requests.RequestException:
            time.sleep(wait_time);
            wait_time = min(3.0, wait_time * 1.8)
    return {}

def _get_year(date_str):
    if not date_str: return None
    try: return int(date_str.split("-")[0])
    except (ValueError, IndexError): return None

def _is_cache_valid(filepath, days=CACHE_EXPIRATION_DAYS):
    if not os.path.exists(filepath): return False
    return (time.time() - os.path.getmtime(filepath)) < (days * 86400)

_genres_cache = None
def _get_genres_cached():
    global _genres_cache
    if _genres_cache: return _genres_cache
    if _is_cache_valid(GENRES_CACHE_FILE):
        with open(GENRES_CACHE_FILE, 'r', encoding='utf-8') as f: _genres_cache = json.load(f); return _genres_cache
    mg=_tmdb_request("/genre/movie/list",{"language":"pt-BR"}).get("genres",[]); tg=_tmdb_request("/genre/tv/list",{"language":"pt-BR"}).get("genres",[])
    genres={"movie_genres":{g["id"]:g["name"] for g in mg},"tv_genres":{g["id"]:g["name"] for g in tg}}
    with open(GENRES_CACHE_FILE, 'w', encoding='utf-8') as f: json.dump(genres,f,ensure_ascii=False,indent=2)
    _genres_cache = genres; return genres

# --- Funções de Construção de Catálogo (Ocultadas para brevidade) ---
def _discover_page(task):
    kind, g, s, d, p, lang, all_g, keywords = task; d0, d1 = d;
    params={"language":lang,"sort_by":s,"page":p,"include_adult":"false","vote_count.gte":100}
    if keywords: params["with_keywords"] = keywords
    data = _tmdb_request(f"/discover/{kind}", params)
    g_map = all_g["movie_genres"] if kind == "movie" else all_g["tv_genres"]
    dk, tk, otk = ("release_date","title","original_title") if kind == "movie" else ("first_air_date","name","original_name")
    res=[]
    for it in data.get("results",[]):
        g_list=[g_map.get(gid) for gid in it.get("genre_ids",[]) if g_map.get(gid)]
        res.append({"id":it["id"],"type":kind,"title":it.get(tk) or it.get(otk) or "","genres":"|".join(g_list),"year":_get_year(it.get(dk)),"runtime":None,"vote_avg":float(it.get("vote_average",0.0)),"vote_cnt":int(it.get("vote_count",0)),"popularity":float(it.get("popularity",0.0))})
    return res, (data.get("page",0) < data.get("total_pages",0))
def _fetch_live_catalog(target, lang, workers):
    g=_get_genres_cached(); m_ids_map={name:gid for gid,name in g["movie_genres"].items()}; t_ids_map={name:gid for gid,name in g["tv_genres"].items()}; m_ids=list(m_ids_map.values()); t_ids=list(t_ids_map.values()); series_priority_tasks = []
    anime_keyword = "210024"; anime_genres = [t_ids_map.get(g) for g in ["Animação", "Ação e Aventura", "Sci-Fi & Fantasy"] if g in t_ids_map]
    if anime_genres:
        for sort_key in ["popularity.desc", "vote_average.desc"]:
            for page in range(1, 11): series_priority_tasks.append(("tv", anime_genres, sort_key, ("2000-01-01", "2025-12-31"), page, lang, g, anime_keyword))
    for sort_key in ["popularity.desc", "vote_average.desc"]:
        for genre_chunk in [t_ids[i:i+2] for i in range(0,len(t_ids),2)]:
            for page in range(1, 4): series_priority_tasks.append(("tv", genre_chunk, sort_key, ("2010-01-01", "2025-12-31"), page, lang, g, None))
    general_tasks = []
    decades=[("1990-01-01","1999-12-31"),("2000-01-01","2009-12-31"),("2010-01-01","2019-12-31"),("2020-01-01","2025-12-31")]; sorts=["vote_average.desc","popularity.desc"]
    for d in decades:
        for s in sorts:
            shuffled_m_ids = random.sample(m_ids, len(m_ids)); shuffled_t_ids = random.sample(t_ids, len(t_ids))
            for chunk in [shuffled_m_ids[i:i+2] for i in range(0,len(shuffled_m_ids),2)]: general_tasks.append(("movie",chunk,s,d,1,lang,g,None))
            for chunk in [shuffled_t_ids[i:i+2] for i in range(0,len(shuffled_t_ids),2)]: general_tasks.append(("tv",chunk,s,d,1,lang,g,None))
    random.shuffle(series_priority_tasks); random.shuffle(general_tasks); tasks=deque(series_priority_tasks + general_tasks); catalog,seen_ids=[],set()
    with Progress(SpinnerColumn(style="primary"),TextColumn("[progress.description]{task.description}"),BarColumn(bar_width=None),TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),TextColumn("• {task.completed}/{task.total} títulos"),TimeElapsedColumn(),console=console,transient=True) as prog:
        task_id=prog.add_task(f"[dim]Buscando na API TMDB...[/]", total=target)
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            futures={ex.submit(_discover_page,tasks.popleft()):tasks[0] for _ in range(min(len(tasks),workers*2))}
            while futures and len(catalog)<target:
                done,_=cf.wait(futures,return_when=cf.FIRST_COMPLETED)
                for fut in done:
                    orig_task=futures.pop(fut)
                    try:
                        batch,has_more=fut.result(); added=0
                        for item in batch:
                            key=(item["type"],item["id"]);
                            if key not in seen_ids: seen_ids.add(key); catalog.append(item); added+=1
                        prog.update(task_id,advance=added)
                        (kind,gn,s,d,p,ln,gs,kw)=orig_task
                        if has_more and added > 0 and p < 15 and len(catalog) < target: tasks.append((kind,gn,s,d,p+1,ln,gs,kw))
                    except Exception: pass
                    if tasks and len(futures)<workers*2: futures[ex.submit(_discover_page,tasks.popleft())]=tasks[0]
    return catalog[:target]
def build_catalog_cached(target, force_rebuild):
    if not force_rebuild and _is_cache_valid(CATALOG_CACHE_FILE):
        with console.status(f"[dim]Carregando catálogo local...[/]", spinner="dots"):
            with open(CATALOG_CACHE_FILE, 'r', encoding='utf-8') as f: catalog = json.load(f)
        console.print(f"[success]✓[/] Catálogo pronto com {len(catalog)} títulos.")
        return catalog
    console.print(f"[warning]![/] Cache do catálogo inválido. Buscando da API (pode levar alguns minutos)...")
    catalog = _fetch_live_catalog(target,"pt-BR",10)
    with open(CATALOG_CACHE_FILE, 'w', encoding='utf-8') as f: json.dump(catalog,f,ensure_ascii=False)
    console.print(f"[success]✓[/] Catálogo pronto com {len(catalog)} títulos.")
    return catalog

# --- Funções de Busca Específica (Ocultadas para brevidade) ---
def _get_search_id(name: str, path: str) -> Optional[str]:
    if not name or _norm(name) == "nenhum": return None # (CORRIGIDO) Ignora "nenhum"
    params = {"language": "pt-BR", "query": name}
    data = _tmdb_request(path, params)
    results = data.get("results", [])
    if results: return str(results[0]["id"])
    console.print(f"[warning]Aviso: Termo '{name}' não encontrado em {path}.[/]")
    return None
def _get_keyword_ids(terms: List[str]) -> Optional[str]:
    ids = []
    for term in terms:
        if not term or _norm(term) == "nenhum": continue # (CORRIGIDO) Ignora "nenhum"
        params = {"query": term}
        data = _tmdb_request("/search/keyword", params)
        results = data.get("results", [])
        if results: ids.append(str(results[0]["id"]))
        else: console.print(f"[warning]Aviso: Palavra-chave '{term}' não encontrada.[/]")
    return ",".join(ids) if ids else None
def _build_discover_params(prefs: Dict[str, Any]) -> Dict[str, Any]:
    g = _get_genres_cached(); m_ids_map = {name: gid for gid, name in g["movie_genres"].items()}; t_ids_map = {name: gid for gid, name in g["tv_genres"].items()}; inc_ids_m = [str(m_ids_map[name]) for name in prefs["inc"] if name in m_ids_map]; inc_ids_t = [str(t_ids_map[name]) for name in prefs["inc"] if name in t_ids_map]; exc_ids_m = [str(m_ids_map[name]) for name in prefs["exc"] if name in m_ids_map]; exc_ids_t = [str(t_ids_map[name]) for name in prefs["exc"] if name in t_ids_map]; inc_genres, exc_genres = [], []
    if prefs["type"] == "movie": inc_genres, exc_genres = inc_ids_m, exc_ids_m
    elif prefs["type"] == "tv": inc_genres, exc_genres = inc_ids_t, exc_ids_t
    else: inc_genres, exc_genres = list(set(inc_ids_m + inc_ids_t)), list(set(exc_ids_m + exc_ids_t))
    params = {"language": "pt-BR", "include_adult": "false", "vote_count.gte": 150}
    if inc_genres: params["with_genres"] = ",".join(inc_genres)
    if exc_genres: params["without_genres"] = ",".join(exc_genres)
    with console.status(f"[dim]Traduzindo termos da API...[/]", spinner="dots"):
        if prefs.get("keywords_raw"):
            if keyword_ids := _get_keyword_ids(prefs["keywords_raw"]): params["with_keywords"] = keyword_ids
        if prefs.get("actor_raw"):
            if person_id := _get_search_id(prefs["actor_raw"], "/search/person"): params["with_cast"] = person_id
        if prefs.get("director_raw"):
            if person_id := _get_search_id(prefs["director_raw"], "/search/person"): params["with_crew"] = person_id
        if prefs.get("company_raw"):
            if company_id := _get_search_id(prefs["company_raw"], "/search/company"): params["with_companies"] = company_id
        if prefs.get("network_raw"):
            if network_id := _get_search_id(prefs["network_raw"], "/search/network"): params["with_networks"] = network_id
        if prefs.get("year_raw"):
            params["primary_release_year" if prefs["type"] != "tv" else "first_air_date_year"] = prefs["year_raw"]
        if prefs.get("min_vote_raw"):
             params["vote_average.gte"] = prefs["min_vote_raw"]
        if prefs.get("rating_raw") and prefs.get("rating_raw") != "NENHUM": # (CORRIGIDO)
            params["certification_country"] = "BR"; params["certification.lte"] = prefs["rating_raw"]
    if "primary_release_year" not in params and "first_air_date_year" not in params:
        if prefs.get("classic_focus"):
            params["primary_release_date.lte" if prefs["type"] != "tv" else "first_air_date.lte"] = "2000-01-01"; params["sort_by"] = "vote_average.desc"
        elif prefs.get("prefer_new"):
            params["primary_release_date.gte" if prefs["type"] != "tv" else "first_air_date.gte"] = "2010-01-01"; params["sort_by"] = "popularity.desc"
    if "sort_by" not in params:
        if prefs["w_rating"] > prefs["w_pop"]: params["sort_by"] = "vote_average.desc"
        else: params["sort_by"] = "popularity.desc"
    return params
def _fetch_live_discover(kind: str, params: Dict[str, Any], target_pages=3) -> List[Dict]:
    catalog = []; seen_ids = set(); g_map = _get_genres_cached()["movie_genres"] if kind == "movie" else _get_genres_cached()["tv_genres"]; dk, tk, otk = ("release_date", "title", "original_title") if kind == "movie" else ("first_air_date", "name", "original_name")
    with Progress(SpinnerColumn(style="primary"), TextColumn("[progress.description]{task.description}"), BarColumn(), TextColumn("{task.completed}/{task.total} págs"), console=console, transient=True) as prog:
        task_id = prog.add_task(f"[dim]Buscando '{kind}' ao vivo...[/]", total=target_pages)
        for p in range(1, target_pages + 1):
            params["page"] = p
            data = _tmdb_request(f"/discover/{kind}", params)
            results = data.get("results", [])
            if not results: break 
            for it in results:
                key = (kind, it["id"])
                if key not in seen_ids:
                    seen_ids.add(key)
                    g_list = [g_map.get(gid) for gid in it.get("genre_ids", []) if g_map.get(gid)]
                    catalog.append({"id": it["id"], "type": kind, "title": it.get(tk) or it.get(otk) or "", "genres": "|".join(g_list), "year": _get_year(it.get(dk)), "runtime": None, "vote_avg": float(it.get("vote_average", 0.0)), "vote_cnt": int(it.get("vote_count", 0)), "popularity": float(it.get("popularity", 0.0))})
            prog.update(task_id, advance=1)
    return catalog

# --- Lógica de Pontuação (Ocultada para brevidade) ---
GEN_CANON=["Ação","Aventura","Animação","Comédia","Crime","Documentário","Drama","Família","Fantasia","História","Terror","Música","Mistério","Romance","Ficção Científica","Cinema TV","Thriller","Guerra","Faroeste"]; THEMES={"heist":["Crime","Ação"],"espacial":["Ficção Científica","Aventura"],"medieval":["Fantasia","História"],"super-heroi":["Ação","Aventura","Fantasia"],"politica":["Drama","Thriller"],"biografia":["Drama","História"],"noir":["Crime","Mistério"],"musical":["Música","Romance"],"suspense":["Thriller","Mistério"]}
def map_terms_to_genres(terms):
    out=set(); norm_canon=[_norm(g) for g in GEN_CANON]
    for term in terms:
        if not term or _norm(term) == "nenhum": continue # (CORRIGIDO) Ignora "nenhum"
        norm_term=_norm(term);
        for theme_key, theme_genres in THEMES.items():
            if fuzz.partial_ratio(norm_term,theme_key)>85: out.update(theme_genres)
        best=process.extractOne(norm_term,norm_canon,scorer=fuzz.token_set_ratio)
        if best and best[1]>75: out.add(GEN_CANON[best[2]])
    return list(out)
def get_duration_score(pref, runtime):
    if runtime is None: return 0.5 
    t=_norm(pref or "");
    if "curt" in t: return max(0.0, 1 - abs(runtime - 90) / 90)
    if "medi" in t: return max(0.0, 1 - abs(runtime - 120) / 60)
    if "long" in t: return max(0.0, 1 - abs(runtime - 180) / 180)
    return 0.5
TYPE_MATCH_STRONG_BONUS = 60
def score_item(item, prefs):
    s=0.0; i_g_norm=_norm(item["genres"])
    if prefs["type"] and prefs["type"] == item["type"]: s += TYPE_MATCH_STRONG_BONUS
    for g_norm in prefs["inc_norm"]:
        if g_norm in i_g_norm: s+=15
    for g_norm in prefs["exc_norm"]:
        if g_norm in i_g_norm: s-=25
    s+=10 * get_duration_score(prefs["dur"], item.get("runtime"))
    q = (item["vote_avg"] / 10.0) * (min(1.0, item["vote_cnt"] / 5000.0));
    p = min(1.0, item["popularity"] / 1000.0)
    s += prefs["w_rating"] * q * 12; s += prefs["w_pop"] * p * 12
    y = item.get("year") or 2000
    if "classic_focus" in prefs and prefs["classic_focus"]: s += max(0, (2000 - y) / 10)
    elif prefs["prefer_new"]: s += max(0, (y - 2000) / 3)
    else: s -= max(0, (y - 2010) / 4)
    return s

# --- Extração de Detalhes e IA (Ocultadas para brevidade) ---
def _parse_certification(data: Dict, kind: str) -> str:
    try:
        if kind == "movie":
            releases = data.get("release_dates", {}).get("results", [])
            for r in releases:
                if r.get("iso_3166_1") == "BR":
                    for certification in r.get("release_dates", []):
                        if c := certification.get("certification"): return c
        else: # kind == "tv"
            ratings = data.get("content_ratings", {}).get("results", [])
            for r in ratings:
                if r.get("iso_3166_1") == "BR": return r.get("rating")
    except Exception: pass
    return "N/A"
def _fetch_details_concurrent(items_to_detail: List[Dict]) -> List[Dict]:
    def fetch_one(item):
        kind = item['type']; append_params = "credits,watch/providers,keywords,recommendations"
        if kind == "movie": append_params += ",release_dates"
        else: append_params += ",content_ratings"
        path = f"/{kind}/{item['id']}"
        data = _tmdb_request(path, params={"language": "pt-BR", "append_to_response": append_params})
        if not data: return item
        if kind == "movie": item["runtime"] = data.get("runtime")
        else: r = data.get("episode_run_time", []); item["runtime"] = int(sum(r) / len(r)) if r else None
        item["synopsis"] = data.get("overview") or "Sinopse não disponível."
        if kind == "movie":
            directors = [c["name"] for c in data.get("credits", {}).get("crew", []) if c.get("job") == "Director"]
            item["director"] = ", ".join(directors[:2]) if directors else "N/A"
        else:
            creators = [c["name"] for c in data.get("created_by", [])]
            item["director"] = ", ".join(creators[:2]) if creators else "N/A"
        cast = [c["name"] for c in data.get("credits", {}).get("cast", [])[:4]]; item["cast"] = ", ".join(cast) if cast else "N/A"
        providers_data = data.get("watch/providers", {}).get("results", {}).get("BR", {}); streaming_providers = [p["provider_name"] for p in providers_data.get("flatrate", [])]
        if streaming_providers: item["providers"] = ", ".join(list(dict.fromkeys(streaming_providers)))
        else: item["providers"] = "Não encontrado em streaming (assinatura)"
        kw_data = data.get("keywords", {}); kw_list = kw_data.get("keywords", kw_data.get("results", [])); item["keywords"] = ", ".join([k["name"] for k in kw_list[:5]]) if kw_list else "N/A"
        rec_data = data.get("recommendations", {}).get("results", [])
        if rec_data: rec_names = [r.get("title") or r.get("name") for r in rec_data[:3] if r.get("title") or r.get("name")]; item["recommendations"] = ", ".join(rec_names)
        else: item["recommendations"] = "Nenhuma recomendação similar encontrada."
        item["tagline"] = data.get("tagline") or ""; item["rating_br"] = _parse_certification(data, kind); item["companies"] = ", ".join([c["name"] for c in data.get("production_companies", [])[:2]])
        if kind == "tv": item["seasons"] = data.get("number_of_seasons"); item["episodes"] = data.get("number_of_episodes")
        return item
    with cf.ThreadPoolExecutor(max_workers=4) as ex: return list(ex.map(fetch_one, items_to_detail))
COMMENT_TEMPLATES = {"Ação": ["...pura octanagem."],"Aventura": ["...jornada épica."],"Comédia": ["Gargalhadas garantidas..."],"Drama": ["...história emocionante."],"Ficção Científica": ["...expande a mente."],"Terror": ["...luzes acesas."],"Romance": ["...para aquecer o coração."],"Mistério": ["...quebra-cabeça."],"Animação": ["...deslumbrante."],"default": ["...merece uma chance."]}
QUALIFIER_PHRASES = {"acclaimed": ["Aclamado pela crítica..."],"popular": ["O título do momento..."],"underrated": ["Uma joia subestimada..."],"classic": ["Um verdadeiro clássico..."]}
def generate_ai_comment_local(item: Dict) -> str:
    genres = item.get("genres", "").split("|"); primary_genre = genres[0] if genres else "default"; comment_parts = []; templates = COMMENT_TEMPLATES.get(primary_genre, COMMENT_TEMPLATES["default"]); comment_parts.append(random.choice(templates))
    if item.get("vote_avg", 0) >= 8.2: comment_parts.append(random.choice(QUALIFIER_PHRASES["acclaimed"]))
    elif (item.get("year", 2025) or 2025) < 2000: comment_parts.append(random.choice(QUALIFIER_PHRASES["classic"]))
    elif item.get("popularity", 0) > 1000: comment_parts.append(random.choice(QUALIFIER_PHRASES["popular"]))
    elif 6.8 <= item.get("vote_avg", 0) < 7.8: comment_parts.append(random.choice(QUALIFIER_PHRASES["underrated"]))
    return " ".join(comment_parts)


# --- Componentes de UI e Interação ---

def banner():
    """Imprime o banner inicial com o novo design."""
    console.print(Panel(Text("🎬 CineAI", style="highlight", justify="center"),
                        box=ROUNDED, padding=(1, 0), border_style="primary"))
    console.print(Text("As melhores sugestões para você!", style="info", justify="center"))

def get_match_color(score_pct: float) -> Style:
    """Retorna um estilo de cor baseado na pontuação."""
    if score_pct > 92: return Style(color="#00FF7F")
    if score_pct > 80: return Style(color="#ADFF2F")
    if score_pct > 65: return "warning"
    return Style(color="#FFA07A")

def show_results(scored_items: List[tuple], top_n=3, is_live_search: bool = False):
    """Exibe os resultados formatados com o máximo de detalhes e design."""
    if not scored_items:
        console.print(f"\n[warning]Nenhum resultado encontrado[/] para essa combinação de filtros. Tente novamente.")
        return
    
    scores = [s for s, _ in scored_items]; min_s, max_s = min(scores), max(scores)
    
    table_title_text = "Top 3 (Busca Específica API)" if is_live_search else "Resumo (Busca Local)"
    summary_table = Table(title=Text(table_title_text, style="title"),
                            header_style="secondary",
                            box=ROUNDED,
                            border_style="dim")
    
    summary_table.add_column("Compatibilidade", justify="center", width=15); summary_table.add_column("Tipo", width=5); summary_table.add_column("Título", min_width=20, overflow="fold")
    summary_table.add_column("Ano", width=4); summary_table.add_column("Gêneros", overflow="fold"); summary_table.add_column("🕒", justify="center", width=7); summary_table.add_column("⭐", justify="center", width=5)

    for score, item in scored_items[:top_n]:
        if is_live_search: pct_text = Text(f"#{scores.index(score)+1} API", style=get_match_color(95))
        else: pct = 40 + (score - min_s) / (max_s - min_s + 1e-6) * 59 if max_s > min_s else 95.0; pct_text = Text(f"{pct:.1f}%", style=get_match_color(pct))
        
        tipo_style="success" if item["type"]=="movie" else "secondary"
        tipo=f"[bold {tipo_style}]{'FILME' if item['type']=='movie' else 'SÉRIE'}[/]"
        runtime=f"{item.get('runtime')}m" if item.get('runtime') else f"[dim]N/A[/]"
        nota_style = get_match_color(item['vote_avg'] * 10)
        
        summary_table.add_row(pct_text, tipo, Text(item["title"], style="text"), str(item.get("year","")),
                        Text(item["genres"].replace("|",", "), style="dim"), runtime, Text(f"{item['vote_avg']:.1f}", style=nota_style))
    
    console.print(summary_table)
    console.print(Rule(style="dim", characters="·"))

    for i, (_, item) in enumerate(scored_items[:top_n], 1):
        
        title = Text.from_markup(f"[bold]#{i} {item['title']}[/] [dim]({item.get('year', 'N/A')})[/]")
        if tagline := item.get("tagline"):
            title.append(Text(f"\n \"{tagline}\"", style="warning italic"))
            
        synopsis_str = item.get('synopsis', 'Sinopse não disponível.')
        synopsis_style = "dim" if "não disponível" in synopsis_str else "text"
        synopsis = Text(f"\n  {synopsis_str}\n", style=synopsis_style, justify="full")

        details_grid = Table.grid(padding=(0, 1)); details_grid.add_column(width=16); details_grid.add_column()
        director_label = 'Diretor:' if item['type'] == 'movie' else 'Criador:'
        providers_str = item.get('providers', 'N/A'); director_str = item.get('director', 'N/A'); cast_str = item.get('cast', 'N/A'); keywords_str = item.get('keywords', 'N/A'); recs_str = item.get('recommendations', 'N/A'); rating_str = item.get('rating_br', 'N/A'); companies_str = item.get('companies', 'N/A')
        providers_style = "text" if "Não encontrado" not in providers_str else "dim"; director_style = "text" if director_str != 'N/A' else "dim"; cast_style = "text" if cast_str != 'N/A' else "dim"; keywords_style = "text" if keywords_str != 'N/A' else "dim"; recs_style = "text" if "Nenhuma" not in recs_str else "dim"; rating_style = "text" if rating_str != 'N/A' else "dim"; companies_style = "text" if companies_str else "dim"
        
        details_grid.add_row(f"[prompt]Onde Ver (BR):[/]", Text(providers_str, style=providers_style))
        details_grid.add_row(f"[prompt]{director_label}[/]", Text(director_str, style=director_style))
        details_grid.add_row(f"[prompt]Elenco:[/]", Text(cast_str, style=cast_style))
        details_grid.add_row(f"[prompt]Classificação:[/]", Text(rating_str, style=rating_style))
        if item['type'] == 'tv': details_grid.add_row(f"[prompt]Temporadas:[/]", Text(f"{item.get('seasons', 'N/A')} ({item.get('episodes', 'N/A')} eps)", style="text"))
        details_grid.add_row(f"[prompt]Produtora(s):[/]", Text(companies_str, style=companies_style))
        details_grid.add_row(f"[prompt]Palavras-chave:[/]", Text(keywords_str, style=keywords_style))
        details_grid.add_row(f"[prompt]Similares:[/]", Text(recs_str, style=recs_style))

        ai_comment = Text.from_markup(f"\n[primary b]💬 Comentário do CineAI:[/]\n[i]{item.get('ai_comment', '...')}[/i]")
        
        render_group = Group(synopsis, details_grid, ai_comment)

        console.print(Panel(render_group, 
                            title=title, 
                            title_align="left", 
                            box=ROUNDED, 
                            border_style="primary",
                            padding=(1, 1)))

def fuzzy_prompt(prompt_text, choices, default=None, threshold=70, explanation=""):
    """
    (CORRIGIDO v4) Um prompt que aceita respostas "fuzzy" e usa o tema.
    Constrói um prompt de texto único para evitar bugs de renderização no Colab.
    """
    prompt_render = Text.from_markup(f"[prompt]❯ {prompt_text}[/] [info]({explanation})[/]")
    
    while True:
        user_input = Prompt.ask(prompt_render, default=default, show_default=True)
        
        if not user_input: user_input = default
        if not user_input:
            console.print(f"  [error]Esta resposta não pode ser vazia.[/error]")
            continue

        norm_input=_norm(user_input); norm_choices=[_norm(c) for c in choices]
        best=process.extractOne(norm_input,norm_choices,scorer=fuzz.token_set_ratio)
        
        if best and best[1]>=threshold:
            return choices[best[2]]
        else:
            console.print(f"  [error]Opção '[white]{user_input}[/white]' não reconhecida.[/error]")


# --- (CORRIGIDO) Lógica do Painel de Perguntas ---

def ask_preferences_panel() -> Dict[str, Any]:
    """(CORRIGIDO) Exibe o formulário de perguntas GENÉRICAS com o prompt estável."""
    console.print(Panel(Text("Busca Normal", style="title", justify="center"),
                        subtitle="Baseada no Cache Local", 
                        box=ROUNDED, 
                        border_style="secondary"))
    console.print(Text("Responda às perguntas genéricas para calibrar as recomendações.", style="info", justify="center"))
    console.print("")
    tipo_map={"Filme":"movie","Série":"tv","Tanto faz":""}; foco_map={"Nota":(1.0,0.4),"Popularidade":(0.4,1.0),"Equilíbrio":(0.8,0.8)}
    
    tipo = fuzzy_prompt("Qual o formato?", choices=list(tipo_map.keys()), default="Tanto faz", explanation="[b]F[/b]ilme / [b]S[/b]érie / [b]T[/b]anto faz")
    foco = fuzzy_prompt("Qual o seu foco?", choices=list(foco_map.keys()), default="Equilíbrio", explanation="[b]N[/b]ota / [b]P[/b]opularidade / [b]E[/b]quilíbrio")
    
    # (CORRIGIDO) Adiciona default="Nenhum"
    prompt_render = Text.from_markup(f"[prompt]❯ Gêneros ou temas que você curte?[/] [info](Separe por vírgulas)[/]")
    inc_raw = Prompt.ask(prompt_render, default="Nenhum")
    
    # (CORRIGIDO) Adiciona default="Nenhum"
    prompt_render = Text.from_markup(f"[prompt]❯ Gêneros ou temas para evitar?[/] [info](Separe por vírgulas)[/]")
    exc_raw = Prompt.ask(prompt_render, default="Nenhum")

    dur = fuzzy_prompt("Qual a duração ideal?", choices=["Curta", "Média", "Longa", "Qualquer"], default="Qualquer", explanation="[b]C[/b]urta / [b]M[/b]édia / [b]L[/b]onga / [b]Q[/b]ualquer")
    
    # (CORRIGIDO) Usa fuzzy_prompt em vez de Confirm.ask
    prefer_new_str = fuzzy_prompt("Dar preferência a títulos recentes (pós 2010)?", 
                                  choices=["Sim", "Não"], 
                                  default="Não", 
                                  explanation="[b]S[/b]im / [b]N[/b]ão")
    prefer_new = (prefer_new_str == "Sim")
    
    w_r,w_p=foco_map[foco]; inc_g=map_terms_to_genres(re.split(r"[,;\|/]+",inc_raw)); exc_g=map_terms_to_genres(re.split(r"[,;\|/]+",exc_raw))
    console.print(f"\n[dim]Gêneros mapeados: Incluindo [warning]{inc_g or 'Nenhum'}[/] | Excluindo [error]{exc_g or 'Nenhum'}[/dim]")
    return {"type":tipo_map[tipo],"inc":inc_g,"exc":exc_g,"inc_norm":[_norm(g) for g in inc_g],"exc_norm":[_norm(g) for g in exc_g],
            "dur":dur,"prefer_new":prefer_new,"w_rating":w_r,"w_pop":w_p, "is_specific": False}

def ask_specific_search_panel() -> Dict[str, Any]:
    """(CORRIGIDO) Exibe o formulário de perguntas MÁXIMO com o prompt estável."""
    console.print(Panel(Text("Busca Específica", style="title", justify="center"),
                        subtitle="Direto da API", 
                        box=ROUNDED, 
                        border_style="primary"))
    console.print(Text("Preencha o máximo de campos para a busca mais precisa possível.", style="info", justify="center"))
    console.print("")
    tipo_map={"Filme":"movie","Série":"tv","Tanto faz":""}; foco_map={"Nota":(1.0,0.4),"Popularidade":(0.4,1.0),"Equilíbrio":(0.8,0.8)}
    
    tipo = fuzzy_prompt("Qual o formato?", choices=list(tipo_map.keys()), default="Tanto faz", explanation="[b]F[/b]ilme / [b]S[/b]érie / [b]T[/b]anto faz")
    foco = fuzzy_prompt("Qual o seu foco?", choices=list(foco_map.keys()), default="Equilíbrio", explanation="[b]N[/b]ota / [b]P[/b]opularidade / [b]E[/b]quilíbrio")

    # (CORRIGIDO) Adiciona default="Nenhum"
    prompt_render = Text.from_markup(f"[prompt]❯ Gêneros ou temas que você curte?[/] [info](Separe por vírgulas)[/]")
    inc_raw = Prompt.ask(prompt_render, default="Nenhum")
    prompt_render = Text.from_markup(f"[prompt]❯ Gêneros ou temas para evitar?[/] [info](Separe por vírgulas)[/]")
    exc_raw = Prompt.ask(prompt_render, default="Nenhum")
    
    # (CORRIGIDO) Usa fuzzy_prompt em vez de Confirm.ask
    prefer_new_str = fuzzy_prompt("Dar preferência a títulos recentes (pós 2010)?",
                                  choices=["Sim", "Não"], 
                                  default="Não", 
                                  explanation="[b]S[/b]im / [b]N[/b]ão")
    prefer_new = (prefer_new_str == "Sim")

    console.print(Rule(style="dim", characters="·"))
    console.print(Text("Filtros Específicos", style='subtitle', justify="center"))

    # (CORRIGIDO) Adiciona default="Nenhum" ou "" para campos de texto
    prompt_render = Text.from_markup(f"[prompt]❯ Ano de lançamento específico?[/] [info](Ex: 1999)[/]")
    year_raw = Prompt.ask(prompt_render, default="")
    prompt_render = Text.from_markup(f"[prompt]❯ Nota mínima (0-10)?[/] [info](Ex: 8.5)[/]")
    min_vote_raw = Prompt.ask(prompt_render, default="")
    prompt_render = Text.from_markup(f"[prompt]❯ Classificação indicativa (BR) máxima?[/] [info](Ex: L, 10, 12, 14, 16, 18)[/]")
    rating_raw = Prompt.ask(prompt_render, default="Nenhum").upper()
    
    prompt_render = Text.from_markup(f"[prompt]❯ Tema ou palavra-chave específica?[/] [info](Ex: cyberpunk, viagem no tempo. (Separe por vírgulas))[/]")
    keywords_raw = Prompt.ask(prompt_render, default="Nenhum")
    
    prompt_render = Text.from_markup(f"[prompt]❯ Incluir algum ator ou atriz?[/] [info](Ex: Tom Hanks, Cillian Murphy)[/]")
    actor_raw = Prompt.ask(prompt_render, default="Nenhum")
    prompt_render = Text.from_markup(f"[prompt]❯ Incluir algum diretor(a)?[/] [info](Ex: Christopher Nolan, Greta Gerwig)[/]")
    director_raw = Prompt.ask(prompt_render, default="Nenhum")
    prompt_render = Text.from_markup(f"[prompt]❯ De qual Produtora ou Estúdio?[/] [info](Ex: A24, Marvel, Ghibli, Blumhouse)[/]")
    company_raw = Prompt.ask(prompt_render, default="Nenhum")
    prompt_render = Text.from_markup(f"[prompt]❯ De qual Rede ou Streaming?[/] [info](Ex: HBO, Netflix, Apple TV+, FX)[/]")
    network_raw = Prompt.ask(prompt_render, default="Nenhum")
    
    w_r,w_p=foco_map[foco]; inc_g=map_terms_to_genres(re.split(r"[,;\|/]+",inc_raw)); exc_g=map_terms_to_genres(re.split(r"[,;\|/]+",exc_raw))
    console.print(f"\n[dim]Gêneros mapeados: Incluindo [warning]{inc_g or 'Nenhum'}[/] | Excluindo [error]{exc_g or 'Nenhum'}[/dim]")
    return {"type":tipo_map[tipo],"inc":inc_g,"exc":exc_g,"inc_norm":[_norm(g) for g in inc_g],"exc_norm":[_norm(g) for g in exc_g],
            "dur":"Qualquer","prefer_new":prefer_new,"w_rating":w_r,"w_pop":w_p,
            "keywords_raw": [k.strip() for k in re.split(r"[,;\|/]+", keywords_raw) if k.strip() and _norm(k) != "nenhum"], # (CORRIGIDO)
            "actor_raw": actor_raw.strip(), "director_raw": director_raw.strip(),
            "company_raw": company_raw.strip(), "network_raw": network_raw.strip(),
            "year_raw": year_raw.strip(), "min_vote_raw": min_vote_raw.strip(),
            "rating_raw": rating_raw.strip(), "is_specific": True}

# --- Fluxo Principal (CLI) ---

def cli(args):
    """Função principal que controla o fluxo da aplicação."""
    console.clear(); banner()
    
    try: _get_genres_cached()
    except Exception as e:
        console.print(f"[error]ERRO CRÍTICO: Falha ao carregar gêneros da API ou cache. Verifique a conexão/chave. Detalhe: {e}[/error]"); return

    catalog_base = build_catalog_cached(args.target, args.rebuild)
    if not catalog_base:
        console.print(Panel(f"[error]Falha ao construir o catálogo base.[/]", box=ROUNDED, border_style='error')); return

    console.print(Rule(style="dim"))
    
    prefs = ask_preferences_panel()

    while True:
        scored_items = []
        is_live_search = prefs.get("is_specific", False) 

        if is_live_search:
            console.print(f"\n[primary b]![/] Busca específica ativada. Consultando a API ao vivo...")
            api_params = _build_discover_params(prefs)
            live_catalog = []
            if prefs["type"] == "movie": live_catalog = _fetch_live_discover("movie", api_params.copy())
            elif prefs["type"] == "tv": live_catalog = _fetch_live_discover("tv", api_params.copy())
            else: 
                live_catalog.extend(_fetch_live_discover("movie", api_params.copy(), target_pages=2))
                live_catalog.extend(_fetch_live_discover("tv", api_params.copy(), target_pages=2))
            scored_items = [(100 - i, item) for i, item in enumerate(live_catalog)]
        else:
            console.print(f"\n[dim]Buscando no catálogo local de {len(catalog_base)} títulos...[/]")
            with console.status(f"[dim]🧠 Calculando recomendações...[/]", spinner="dots"):
                scored_items = sorted([(score_item(item, prefs), item) for item in catalog_base], key=lambda x:x[0], reverse=True)
        
        top_items = [item for _, item in scored_items[:3]]
        if top_items:
            with console.status(f"[dim]Buscando o máximo de detalhes (classificação, tagline, etc)...[/]", spinner="dots"):
                _fetch_details_concurrent(top_items)
            for item in top_items:
                item['ai_comment'] = generate_ai_comment_local(item)

        console.print(Rule(style="dim", characters=" "))
        show_results(scored_items, top_n=3, is_live_search=is_live_search)

        console.print("")
        action = fuzzy_prompt("O que fazer agora?", 
                              choices=["Busca Específica (API)", "Nova Busca Normal", "Sair"], 
                              default="Nova Busca Normal",
                              explanation="[b]A[/b]PI (Específica) / [b]N[/b]ormal (Rápida) / [b]S[/b]air")

        if action == "Sair": break
        elif action == "Nova Busca Normal":
            console.print(Rule(style="dim")); 
            prefs = ask_preferences_panel()
        elif action == "Busca Específica (API)":
            console.print(Rule(style="dim")); 
            prefs = ask_specific_search_panel()

    console.print(Panel(Text(f"🍿 Bom filme/série!", style="highlight"), box=ROUNDED, padding=(1, 4), border_style="primary"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CineAI - Recomendações de Filmes e Séries")
    parser.add_argument("--target", type=int, default=2500, help="Número de títulos desejado no catálogo.")
    parser.add_argument("--rebuild", action="store_true", help="Força a reconstrução do cache do catálogo.")
    try: args = parser.parse_args()
    except SystemExit: args = parser.parse_args([])
    
    try:
        if not TMDB_BEARER or "eyJ" not in TMDB_BEARER:
            console.print(f"[error]ERRO: A variável TMDB_BEARER não é uma chave de API válida.[/error]")
        else:
            cli(args)
    except KeyboardInterrupt: 
        console.print(f"\n[error]Encerrado pelo usuário.[/error]")
    except Exception as e: 
        console.print_exception()
