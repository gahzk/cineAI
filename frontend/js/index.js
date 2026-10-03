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
  setupProviderPicker(providers);
}

// ------------------------------------------------------------------
// Janela de streamings: ordem alfabética, busca por nome e salto por letra
// ------------------------------------------------------------------
const plain = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase();
const letterOf = name => (/[A-Z]/.test(plain(name)[0]) ? plain(name)[0] : '#');
let providerNames = new Map();

function setupProviderPicker(providers) {
  const input = document.getElementById('provider');
  const toggle = document.getElementById('provider-toggle');
  const pop = document.getElementById('provider-pop');
  const search = document.getElementById('provider-search');
  const list = document.getElementById('provider-list');
  const az = document.getElementById('provider-az');

  const sorted = [...providers].sort((a, b) => plain(a.name).localeCompare(plain(b.name), 'pt-BR'));
  providerNames = new Map(sorted.map(p => [String(p.id), p.name]));
  const groups = new Map();
  for (const p of sorted) {
    const l = letterOf(p.name);
    if (!groups.has(l)) groups.set(l, []);
    groups.get(l).push(p);
  }
  const option = (id, name) =>
    `<button type="button" class="picker-option" role="option" data-id="${id}" data-name="${esc(plain(name))}">${esc(name)}</button>`;
  const ordered = [...groups].sort(([a], [b]) => (a === '#') - (b === '#')); // números por último, como no A–Z
  list.innerHTML = option('', 'Qualquer serviço') + ordered.map(([l, items]) =>
    `<div class="picker-group" data-letter="${l}"><div class="picker-letter" id="pv-letter-${l}">${l}</div>
      ${items.map(p => option(p.id, p.name)).join('')}</div>`).join('');
  const letters = [...'ABCDEFGHIJKLMNOPQRSTUVWXYZ', '#'];
  az.innerHTML = letters.map(l => `<button type="button" data-letter="${l}" ${groups.has(l) ? '' : 'disabled'}
    aria-label="Ir para ${l === '#' ? 'números' : l}">${l}</button>`).join('');

  const open = show => {
    pop.hidden = !show;
    toggle.setAttribute('aria-expanded', String(show));
    if (show) {
      search.value = '';
      filter('');
      list.querySelector(`[data-id="${input.value}"]`)?.scrollIntoView({ block: 'nearest' });
      search.focus();
    }
  };
  const filter = q => {
    const term = plain(q.trim());
    list.querySelectorAll('.picker-option').forEach(b => { b.hidden = term !== '' && !b.dataset.name.includes(term); });
    list.querySelectorAll('.picker-group').forEach(g => { g.hidden = !g.querySelector('.picker-option:not([hidden])'); });
  };

  toggle.addEventListener('click', () => open(pop.hidden));
  search.addEventListener('input', () => filter(search.value));
  az.addEventListener('click', e => {
    const l = e.target.closest('button')?.dataset.letter;
    if (!l) return;
    search.value = '';
    filter('');
    const head = document.getElementById(`pv-letter-${l}`);
    list.scrollTop = head.parentElement.offsetTop; // a lista é position: relative
    head.parentElement.querySelector('.picker-option')?.focus({ preventScroll: true });
  });
  list.addEventListener('click', e => {
    const b = e.target.closest('.picker-option');
    if (!b) return;
    setProvider(b.dataset.id);
    open(false);
    toggle.focus();
  });
  pop.addEventListener('keydown', e => {
    if (e.key === 'Escape') { open(false); toggle.focus(); }
    // Digitar uma letra com foco na lista pula para ela
    if (e.target !== search && /^[a-z]$/i.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) {
      az.querySelector(`[data-letter="${e.key.toUpperCase()}"]:not([disabled])`)?.click();
    }
  });
  document.addEventListener('click', e => { if (!pop.hidden && !e.target.closest('#provider-picker')) open(false); });
  // O reset do formulário não limpa campo oculto: limpa aqui, e recalcula o contador depois do reset.
  form.addEventListener('reset', () => { setProvider(''); setTimeout(updateAdvancedCount, 0); });
}

function setProvider(id) {
  const input = document.getElementById('provider');
  input.value = id ?? '';
  document.getElementById('provider-current').textContent = providerNames.get(String(input.value)) || 'Qualquer';
  document.querySelectorAll('#provider-list .picker-option').forEach(b => {
    b.setAttribute('aria-selected', String(b.dataset.id === input.value));
  });
  updateAdvancedCount();
}

// Quantos filtros de "Mais filtros" estão ativos, mostrado no título da seção.
function updateAdvancedCount() {
  const f = readForm();
  const n = [f.provider, f.year, f.duration !== 'any', f.actor, f.director, f.keyword, f.min_vote !== null,
    f.rating_br, f.exclude_genres.length].filter(Boolean).length;
  document.getElementById('adv-count').textContent = n ? `· ${n} ${n === 1 ? 'ativo' : 'ativos'}` : '';
  return n;
}
form.addEventListener('input', updateAdvancedCount);
form.addEventListener('change', updateAdvancedCount);

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

let filling = false;

function fillForm(f) {
  filling = true;
  form.reset();
  filling = false;
  for (const [name, value] of Object.entries(f)) {
    const fields = form.elements.namedItem(name);
    if (!fields || value === null || value === undefined) continue;
    if (Array.isArray(value)) {
      form.querySelectorAll(`[name="${name}"]`).forEach(el => { el.checked = value.includes(Number(el.value)); });
    } else {
      fields.value = value; // funciona para input, select e grupo de radios
    }
  }
  setProvider(f.provider ? String(f.provider) : '');
  if (updateAdvancedCount()) form.querySelector('details.advanced').open = true;
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
  if (filling) return; // reset interno do fillForm, não do botão Limpar
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
