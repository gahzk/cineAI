/**
 * api.js — CineAI API client
 * Thin wrapper around fetch() that handles base URL, auth headers and error extraction.
 */
const API_BASE = '/api/v1';

const api = (() => {
  function getToken() {
    return localStorage.getItem('cineai_token') || '';
  }

  function authHeaders() {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
  }

  async function request(method, path, body = null) {
    const opts = {
      method,
      headers: authHeaders(),
    };
    if (body !== null) opts.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE}${path}`, opts);

    // Unauthorised — redirect to login
    if (res.status === 401) {
      localStorage.removeItem('cineai_token');
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
      throw new Error('Sessão expirada. Faça login novamente.');
    }

    let data;
    try { data = await res.json(); } catch { data = {}; }

    if (!res.ok) {
      const detail = data?.detail || data?.message || `Erro ${res.status}`;
      throw new Error(Array.isArray(detail)
        ? detail.map(d => d.msg).join('; ')
        : String(detail));
    }
    return data;
  }

  return {
    // --- Auth ---
    register: (username, email, password) =>
      request('POST', '/auth/register', { username, email, password }),

    login: (email, password) =>
      request('POST', '/auth/login', { email, password }),

    me: () => request('GET', '/auth/me'),

    // --- Recommendations ---
    catalogStatus: () => request('GET', '/recommendations/catalog/status'),

    normalSearch: (payload) =>
      request('POST', '/recommendations/search', payload),

    specificSearch: (payload) =>
      request('POST', '/recommendations/search/specific', payload),

    // --- Analytics ---
    analyticsSummary: () => request('GET', '/analytics/summary'),
  };
})();
