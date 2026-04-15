/**
 * app.js — Main recommendation page logic.
 * Handles form state, API calls, and result rendering.
 */

// ============================================================
// Boot
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  await initNavbar();
  setupRangeInputs();
  setupOptionChips();
  setupSearchTabs();
  setupSearchButtons();
});

// ============================================================
// Range inputs live display
// ============================================================
function setupRangeInputs() {
  [
    ['normal-w-rating', 'normal-w-rating-val'],
    ['normal-w-pop',    'normal-w-pop-val'],
    ['spec-w-rating',   'spec-w-rating-val'],
  ].forEach(([inputId, valId]) => {
    const input = document.getElementById(inputId);
    const valEl = document.getElementById(valId);
    if (!input || !valEl) return;
    input.addEventListener('input', () => { valEl.textContent = input.value; });
  });
}

// ============================================================
// Option chips (single-select toggle)
// ============================================================
function setupOptionChips() {
  document.querySelectorAll('.option-group').forEach(group => {
    group.querySelectorAll('.option-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        group.querySelectorAll('.option-chip').forEach(c => c.classList.remove('selected'));
        chip.classList.add('selected');
      });
    });
  });
}

function getSelectedChip(groupId) {
  const group = document.getElementById(groupId);
  if (!group) return '';
  const selected = group.querySelector('.option-chip.selected');
  return selected ? selected.dataset.value : '';
}

// ============================================================
// Search mode tabs
// ============================================================
function setupSearchTabs() {
  document.querySelectorAll('[data-search-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-search-tab]').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content[id^="search-tab-"]').forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('search-tab-' + btn.dataset.searchTab).classList.add('active');
    });
  });
}

// ============================================================
// Form helpers
// ============================================================
function parseGenreList(inputId) {
  const val = document.getElementById(inputId)?.value || '';
  return val.split(',').map(g => g.trim()).filter(Boolean);
}

function getNormalPayload() {
  const era = getSelectedChip('normal-era');
  return {
    content_type:     getSelectedChip('normal-type'),
    genres_include:   parseGenreList('normal-genres-inc'),
    genres_exclude:   parseGenreList('normal-genres-exc'),
    duration_pref:    getSelectedChip('normal-duration'),
    weight_rating:    parseFloat(document.getElementById('normal-w-rating').value),
    weight_popularity:parseFloat(document.getElementById('normal-w-pop').value),
    prefer_new:       era === 'new',
    classic_focus:    era === 'classic',
    save_preference:  true,
  };
}

function getSpecificPayload() {
  const year = document.getElementById('spec-year').value;
  const minVote = document.getElementById('spec-min-vote').value;
  const rating = document.getElementById('spec-rating-br').value;
  const keyword = document.getElementById('spec-keyword').value.trim();

  return {
    content_type:      getSelectedChip('spec-type'),
    genres_include:    parseGenreList('spec-genres-inc'),
    genres_exclude:    parseGenreList('spec-genres-exc'),
    weight_rating:     parseFloat(document.getElementById('spec-w-rating').value),
    weight_popularity: 0.8,
    keywords:          keyword ? keyword.split(',').map(k => k.trim()).filter(Boolean) : null,
    actor:             document.getElementById('spec-actor').value.trim() || null,
    director:          document.getElementById('spec-director').value.trim() || null,
    company:           document.getElementById('spec-company').value.trim() || null,
    network:           document.getElementById('spec-network').value.trim() || null,
    year:              year ? parseInt(year) : null,
    min_vote:          minVote ? parseFloat(minVote) : null,
    rating_br:         rating || null,
    save_preference:   true,
  };
}

// ============================================================
// Search buttons
// ============================================================
function setupSearchButtons() {
  document.getElementById('btn-normal-search').addEventListener('click', () => runSearch('normal'));
  document.getElementById('btn-spec-search').addEventListener('click', () => runSearch('specific'));
  document.getElementById('btn-normal-clear').addEventListener('click', clearNormalForm);
  document.getElementById('btn-spec-clear').addEventListener('click', clearSpecificForm);
}

function setSearchLoading(mode, loading) {
  const prefix = mode === 'normal' ? 'btn-normal' : 'btn-spec';
  const textEl = document.getElementById(`${prefix}-text`);
  const spinnerEl = document.getElementById(`${prefix}-spinner`);
  const btnEl = document.getElementById(`${mode === 'normal' ? 'btn-normal-search' : 'btn-spec-search'}`);
  textEl.textContent = loading
    ? (mode === 'normal' ? 'Buscando...' : 'Consultando API...')
    : (mode === 'normal' ? 'Buscar recomendações' : 'Buscar na API');
  spinnerEl.classList.toggle('d-none', !loading);
  btnEl.disabled = loading;
}

function showResultsState(state) {
  ['state-empty', 'state-loading', 'state-results', 'state-error'].forEach(id => {
    document.getElementById(id).classList.add('d-none');
  });
  document.getElementById(state).classList.remove('d-none');
}

async function runSearch(mode) {
  setSearchLoading(mode, true);
  showResultsState('state-loading');
  document.getElementById('loading-text').textContent =
    mode === 'normal' ? 'Calculando recomendações...' : 'Consultando a API TMDB...';

  try {
    const payload = mode === 'normal' ? getNormalPayload() : getSpecificPayload();
    const data = mode === 'normal'
      ? await api.normalSearch(payload)
      : await api.specificSearch(payload);

    renderResults(data);
  } catch (err) {
    showResultsState('state-error');
    document.getElementById('error-message').textContent = err.message;
  } finally {
    setSearchLoading(mode, false);
  }
}

// ============================================================
// Clear forms
// ============================================================
function clearNormalForm() {
  document.getElementById('normal-genres-inc').value = '';
  document.getElementById('normal-genres-exc').value = '';
  document.querySelectorAll('#search-tab-normal .option-group').forEach(group => {
    const chips = group.querySelectorAll('.option-chip');
    chips.forEach(c => c.classList.remove('selected'));
    chips[0].classList.add('selected'); // default = first option
  });
  ['normal-w-rating', 'normal-w-pop'].forEach(id => {
    const el = document.getElementById(id);
    el.value = 0.8;
    document.getElementById(id + '-val').textContent = '0.8';
  });
}

function clearSpecificForm() {
  ['spec-keyword','spec-actor','spec-director','spec-company','spec-network','spec-year','spec-min-vote',
   'spec-genres-inc','spec-genres-exc'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('spec-rating-br').value = '';
  document.getElementById('spec-w-rating').value = 0.8;
  document.getElementById('spec-w-rating-val').textContent = '0.8';
  document.querySelectorAll('#search-tab-specific .option-group').forEach(group => {
    const chips = group.querySelectorAll('.option-chip');
    chips.forEach(c => c.classList.remove('selected'));
    chips[0].classList.add('selected');
  });
}

// ============================================================
// Render results
// ============================================================
function renderResults(data) {
  if (!data.results || data.results.length === 0) {
    showResultsState('state-error');
    document.getElementById('error-message').textContent =
      'Nenhum resultado encontrado para essa combinação de filtros.';
    return;
  }

  const modeLabel = data.mode === 'specific' ? 'Busca Específica (API)' : 'Busca Rápida (Catálogo)';
  document.getElementById('results-title').textContent = `Top ${data.results.length} — ${modeLabel}`;
  document.getElementById('results-meta').textContent =
    `${data.total_searched.toLocaleString('pt-BR')} títulos analisados`;

  const grid = document.getElementById('results-grid');
  grid.innerHTML = '';
  data.results.forEach(item => {
    grid.appendChild(buildResultCard(item));
  });

  showResultsState('state-results');
}

function buildResultCard(item) {
  const card = document.createElement('article');
  card.className = 'result-card';

  const typeLabel = item.content_type === 'movie' ? 'FILME' : 'SÉRIE';
  const typeClass = item.content_type === 'movie' ? 'movie' : 'tv';

  const genres = item.genres
    ? item.genres.split('|').filter(Boolean).map(g =>
        `<span class="genre-tag">${g}</span>`
      ).join('')
    : '';

  const runtime = item.runtime ? `${item.runtime}m` : '—';
  const seasons = item.content_type === 'tv' && item.seasons
    ? `<div class="result-meta-label">Temporadas</div><div class="result-meta-value">${item.seasons} (${item.episodes || '—'} eps)</div>`
    : '';

  const providers = item.providers && !item.providers.includes('Não disponível')
    ? `<div class="provider-list">▶ ${item.providers}</div>`
    : `<div class="text-muted" style="font-size:0.8rem">Não encontrado em streaming</div>`;

  card.innerHTML = `
    <div class="result-card-header">
      <div style="flex:1; min-width:0">
        <div class="result-title">${escHtml(item.title)}</div>
        <div class="result-year">${item.year || 'N/A'}</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.4rem;flex-shrink:0">
        <span class="result-rank">#${item.rank}</span>
        <span class="result-type-badge ${typeClass}">${typeLabel}</span>
      </div>
    </div>
    <div class="result-card-body">
      <div class="result-genres">${genres}</div>
      <p class="result-synopsis" id="synopsis-${item.tmdb_id}">${escHtml(item.synopsis || 'Sinopse não disponível.')}</p>
      <div class="result-stats">
        <div class="result-stat"><span class="stat-label">⭐</span><span class="stat-value">${item.vote_avg.toFixed(1)}</span></div>
        <div class="result-stat"><span class="stat-label">🕒</span><span class="stat-value">${runtime}</span></div>
        <div class="result-stat"><span class="stat-label">Score:</span><span class="stat-score font-mono">${item.score.toFixed(1)}</span></div>
      </div>
      <div class="result-meta-grid">
        <div class="result-meta-label">${item.content_type === 'movie' ? 'Diretor' : 'Criador'}</div>
        <div class="result-meta-value">${escHtml(item.director || 'N/A')}</div>
        <div class="result-meta-label">Elenco</div>
        <div class="result-meta-value">${escHtml(item.cast || 'N/A')}</div>
        <div class="result-meta-label">Classificação</div>
        <div class="result-meta-value">${escHtml(item.rating_br || 'N/A')}</div>
        ${seasons}
        <div class="result-meta-label">Palavras-chave</div>
        <div class="result-meta-value text-muted">${escHtml(item.keywords || 'N/A')}</div>
        <div class="result-meta-label">Similares</div>
        <div class="result-meta-value text-muted">${escHtml(item.recommendations || 'N/A')}</div>
      </div>
      ${providers}
    </div>
    <div class="result-card-footer">
      <div class="ai-comment">${escHtml(item.ai_comment || '')}</div>
    </div>
  `;
  return card;
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
