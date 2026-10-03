/**
 * index.js — página de busca: monta o formulário, busca e mostra os resultados e os populares.
 */
const FORM_KEY = 'cineai_last_search';
const form = document.getElementById('search-form');
const resultsEl = document.getElementById('results');

document.addEventListener('DOMContentLoaded', async () => {
  const userPromise = initNavbar();
  loadTrending();
  try {
    const options = await api('GET', '/options');
    renderOptions(options);
    restoreForm();
    setupTextSearch(options.text_search, await userPromise);
  } catch (err) {
    showError(err.message);
  }
});

function renderOptions({ genres, providers }) {
  const chip = (name, g) => `<label class="chip"><input type="checkbox" name="${name}" value="${g.id}"><span>${esc(g.name)}</span></label>`;
  document.getElementById('genres').innerHTML = genres.map(g => chip('genres', g)).join('');
  document.getElementById('exclude-genres').innerHTML = genres.map(g => chip('exclude_genres', g)).join('');
  document.getElementById('provider').insertAdjacentHTML('beforeend',
    providers.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join(''));
}

// ------------------------------------------------------------------
// Formulário <-> objeto de filtros (mesmo formato da API)
// ------------------------------------------------------------------
function readForm() {
  const data = new FormData(form);
  const number = v => (v === '' || v === null ? null : Number(v));
  return {
    content_type: data.get('content_type'),
    era: data.get('era'),
    order: data.get('order'),
    duration: data.get('duration'),
    genres: data.getAll('genres').map(Number),
    exclude_genres: data.getAll('exclude_genres').map(Number),
    provider: number(data.get('provider')),
    keyword: data.get('keyword').trim(),
    actor: data.get('actor').trim(),
    director: data.get('director').trim(),
    year: number(data.get('year')),
    min_vote: number(data.get('min_vote')),
    rating_br: data.get('rating_br'),
  };
}

function fillForm(f) {
  form.reset();
  for (const [name, value] of Object.entries(f)) {
    const fields = form.elements.namedItem(name);
    if (!fields || value === null || value === undefined) continue;
    if (Array.isArray(value)) {
      form.querySelectorAll(`[name="${name}"]`).forEach(el => { el.checked = value.includes(Number(el.value)); });
    } else {
      fields.value = value; // funciona para input, select e grupo de radios
    }
  }
  const f2 = readForm();
  if (f2.keyword || f2.actor || f2.director || f2.year || f2.min_vote || f2.provider || f2.rating_br
      || f2.duration !== 'any' || f2.exclude_genres.length) {
    form.querySelector('details.advanced').open = true;
  }
}

function restoreForm() {
  try {
    const saved = JSON.parse(localStorage.getItem(FORM_KEY) || 'null');
    if (saved) fillForm(saved);
  } catch { /* sem storage ou JSON velho */ }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const filters = readForm();
  try { localStorage.setItem(FORM_KEY, JSON.stringify(filters)); } catch { /* sem storage */ }
  await runSearch('search-btn', () => api('POST', '/search', filters));
});

form.addEventListener('reset', () => {
  try { localStorage.removeItem(FORM_KEY); } catch { /* sem storage */ }
});

// ------------------------------------------------------------------
// Busca por texto (IA)
// ------------------------------------------------------------------
function setupTextSearch(enabled, user) {
  const textForm = document.getElementById('text-form');
  if (!enabled) return;
  textForm.hidden = false;
  if (!user) {
    textForm.querySelector('input').disabled = true;
    document.getElementById('text-btn').disabled = true;
    document.getElementById('text-hint').innerHTML = '<a href="/login.html">Entre na sua conta</a> para descrever o que quer assistir.';
    return;
  }
  textForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = document.getElementById('text-query').value.trim();
    if (text.length < 3) return;
    await runSearch('text-btn', async () => {
      const data = await api('POST', '/search/text', { text });
      fillForm(data.filters);
      document.getElementById('text-hint').textContent =
        'A IA preencheu os filtros abaixo a partir do seu pedido. Ajuste e busque de novo se quiser.';
      return data;
    });
  });
}

// ------------------------------------------------------------------
// Resultados
// ------------------------------------------------------------------
async function runSearch(buttonId, request) {
  const btn = document.getElementById(buttonId);
  const label = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Buscando…';
  resultsEl.innerHTML = '<div class="loading"><span class="spinner"></span>Procurando no TMDB…</div>';
  try {
    renderResults(await request());
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = label;
  }
}

function showError(message) {
  resultsEl.innerHTML = `<div class="alert alert-error" role="alert">${esc(message)}</div>`;
}

function renderResults(data) {
  if (!data.results.length) {
    resultsEl.innerHTML = '<p class="empty">Nada encontrado com esses filtros. Tente tirar um gênero ou um filtro avançado.</p>';
    return;
  }
  resultsEl.innerHTML = `
    <h2 class="section-title">Suas 3 recomendações</h2>
    <p class="results-meta">${data.total_candidates} títulos avaliados</p>
    <div class="results-grid">${data.results.map(resultCard).join('')}</div>`;
  resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resultCard(item, i) {
  const poster = item.poster_url
    ? `<img src="${esc(item.poster_url)}" alt="Pôster de ${esc(item.title)}" loading="lazy">`
    : `<div class="poster-placeholder">${esc(item.title)}</div>`;
  const runtime = item.runtime ? ` · ${item.runtime} min${item.content_type === 'tv' ? ' por episódio' : ''}` : '';
  const seasons = item.seasons ? ` · ${item.seasons} temporada${item.seasons > 1 ? 's' : ''}` : '';
  const where = item.providers?.length
    ? `<p class="where">▶ Onde assistir: ${esc(item.providers.join(', '))}</p>`
    : '<p class="form-hint">Não encontrado em assinatura de streaming no Brasil.</p>';
  const meta = [
    [item.content_type === 'movie' ? 'Direção' : 'Criação', item.director],
    ['Elenco', item.cast],
    ['Classificação', item.rating_br],
  ].filter(([, v]) => v).map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join('');
  const trailer = item.trailer_url
    ? `<a class="btn btn-ghost btn-sm" href="${esc(item.trailer_url)}" target="_blank" rel="noopener">Ver trailer</a>` : '';

  return `<article class="result-card">
    <div class="result-poster">${poster}</div>
    <div class="result-body">
      <div class="result-head">
        <div>
          <h3 class="result-title">${esc(item.title)}</h3>
          <p class="result-sub">${esc(TYPE_LABEL[item.content_type])} · ${esc(item.year || 's/ data')} · ⭐ ${item.vote_avg.toFixed(1)}${runtime}${seasons}</p>
        </div>
        <span class="rank">#${i + 1}</span>
      </div>
      <div class="tags">${item.genres.map(g => `<span class="tag">${esc(g)}</span>`).join('')}</div>
      <div class="why"><strong>Por que recomendamos</strong><ul>${item.reasons.map(r => `<li>${esc(r)}</li>`).join('')}</ul></div>
      <p class="synopsis">${esc(item.synopsis || 'Sinopse não disponível.')}</p>
      ${meta ? `<dl class="meta-grid">${meta}</dl>` : ''}
      ${where}
      <div class="links">
        <a class="btn btn-ghost btn-sm" href="${esc(item.tmdb_url)}" target="_blank" rel="noopener">Ver no TMDB</a>
        ${trailer}
      </div>
    </div>
  </article>`;
}

async function loadTrending() {
  const el = document.getElementById('trending');
  try {
    const { results } = await api('GET', '/trending');
    el.innerHTML = results.map(item => posterCard(item)).join('') || '<p class="empty">Nada em alta agora.</p>';
  } catch (err) {
    el.innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
  }
}
