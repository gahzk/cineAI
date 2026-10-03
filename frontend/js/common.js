/**
 * common.js — usado por todas as páginas: chamadas à API, sessão, navbar e escape de HTML.
 */
const TOKEN_KEY = 'cineai_token';

function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; }
}
function setToken(token) {
  try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY); } catch { /* sem storage */ }
}

/** Escapa texto para uso dentro de innerHTML. Use em TODO dado vindo da API. */
function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

async function api(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  let data = {};
  try { data = await res.json(); } catch { /* resposta sem corpo */ }

  if (res.status === 401 && token) {
    setToken('');
    location.href = '/login.html';
  }
  if (!res.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail)
      ? 'Confira os campos: ' + detail.map(d => d.loc?.at(-1)).join(', ')
      : (detail || `Erro ${res.status}`);
    throw new Error(message);
  }
  return data;
}

/** Busca o usuário logado (ou null) e monta a navbar. Devolve o usuário. */
async function initNavbar() {
  let user = null;
  if (getToken()) {
    try { user = await api('GET', '/auth/me'); } catch { user = null; }
  }
  const area = document.getElementById('navbar-user');
  if (user) {
    area.innerHTML = `<span>Olá, <strong>${esc(user.username)}</strong></span>
      <button class="btn btn-ghost btn-sm" type="button" id="btn-logout">Sair</button>`;
    document.getElementById('btn-logout').addEventListener('click', () => { setToken(''); location.href = '/'; });
  } else {
    area.innerHTML = '<a class="btn btn-primary btn-sm" href="/login.html">Entrar</a>';
  }
  document.querySelectorAll('[data-needs-login]').forEach(el => { el.hidden = !user; });
  document.querySelectorAll('[data-needs-admin]').forEach(el => { el.hidden = !user?.is_admin; });
  const here = location.pathname === '/' ? '/index.html' : location.pathname;
  document.querySelectorAll('.nav-link').forEach(a => {
    if (new URL(a.href).pathname === here) a.setAttribute('aria-current', 'page');
  });
  return user;
}

const TYPE_LABEL = { movie: 'Filme', tv: 'Série' };

function posterCard(item, extra = '') {
  const img = item.poster_url
    ? `<img src="${esc(item.poster_url)}" alt="" loading="lazy">`
    : `<div class="poster-placeholder">${esc(item.title)}</div>`;
  const nota = item.vote_avg ? `⭐ ${item.vote_avg.toFixed(1)}` : '';
  return `<a class="poster-card" href="${esc(item.tmdb_url)}" target="_blank" rel="noopener">
    ${img}
    <div class="poster-card-body">
      <div class="poster-card-title">${esc(item.title)}</div>
      <div class="poster-card-meta">${esc(TYPE_LABEL[item.content_type])} · ${esc(item.year || '')} ${nota}</div>
      ${extra}
    </div>
  </a>`;
}
