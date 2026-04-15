/**
 * dashboard.js — Analytics dashboard logic.
 * Fetches /api/v1/analytics/summary and renders KPIs, charts and tables.
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  await initNavbar();
  await loadDashboard();
});

// ============================================================
// Chart.js global defaults (dark theme)
// ============================================================
Chart.defaults.color = '#9e8899';
Chart.defaults.borderColor = '#3d0020';
Chart.defaults.font.family = "'Inter', sans-serif";

const PALETTE_PRIMARY = [
  '#FF007F','#FF4DA6','#FF80BF',
  '#00B29A','#00D4B8','#00F5D4',
  '#FFD700','#FF8C00','#FF4F4F',
  '#A259FF',
];

// ============================================================
// Main load
// ============================================================
async function loadDashboard() {
  try {
    const data = await api.analyticsSummary();
    renderDashboard(data);
  } catch (err) {
    document.getElementById('dash-loading').classList.add('d-none');
    const errEl = document.getElementById('dash-error');
    errEl.classList.remove('d-none');
    document.getElementById('dash-error-msg').textContent =
      err.message.includes('403')
        ? 'Acesso restrito — apenas administradores podem ver o dashboard.'
        : err.message;
  }
}

// ============================================================
// Render all dashboard sections
// ============================================================
function renderDashboard(d) {
  // KPIs
  document.getElementById('kpi-users').textContent = d.total_users.toLocaleString('pt-BR');
  document.getElementById('kpi-recs').textContent = d.total_recommendations.toLocaleString('pt-BR');
  document.getElementById('kpi-top-genre').textContent =
    d.top_genres.length ? d.top_genres[0].genre : '—';

  // Charts
  renderGenreChart(d.top_genres);
  renderModeChart(d.search_mode_distribution);
  renderWeightChart(d.weight_rating_distribution);

  // Tables
  renderGenreTable(d.top_genres);
  renderTitlesTable(d.top_titles);

  // Insights
  document.getElementById('insight-genre').textContent = d.insight_most_popular_genre;
  document.getElementById('insight-title-text').textContent = d.insight_top_title;
  document.getElementById('insight-search').textContent = d.insight_search_preference;

  // Show content
  document.getElementById('dash-loading').classList.add('d-none');
  document.getElementById('dash-content').classList.remove('d-none');
}

// ============================================================
// Charts
// ============================================================
function renderGenreChart(genres) {
  const ctx = document.getElementById('chart-genres').getContext('2d');
  const top = genres.slice(0, 8);
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: top.map(g => g.genre),
      datasets: [{
        label: 'Aparições',
        data: top.map(g => g.count),
        backgroundColor: top.map((_, i) => PALETTE_PRIMARY[i % PALETTE_PRIMARY.length] + 'CC'),
        borderColor:     top.map((_, i) => PALETTE_PRIMARY[i % PALETTE_PRIMARY.length]),
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#3d0020' }, ticks: { color: '#9e8899' } },
        y: { grid: { color: '#3d0020' }, ticks: { color: '#9e8899' }, beginAtZero: true },
      },
    },
  });
}

function renderModeChart(modes) {
  if (!modes || modes.length === 0) return;
  const ctx = document.getElementById('chart-modes').getContext('2d');
  const labels = modes.map(m => m.mode === 'normal' ? 'Busca Rápida' : 'Busca Específica');
  const data = modes.map(m => m.count);
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: ['#FF007FCC', '#00B29ACC'],
        borderColor:     ['#FF007F', '#00B29A'],
        borderWidth: 2,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 16, usePointStyle: true, color: '#9e8899' },
        },
      },
      cutout: '60%',
    },
  });
}

function renderWeightChart(weights) {
  if (!weights || weights.length === 0) return;
  const ctx = document.getElementById('chart-weights').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: weights.map(w => w.label),
      datasets: [{
        label: 'Usuários',
        data: weights.map(w => w.count),
        backgroundColor: ['#FF007FCC', '#00B29ACC', '#FFD700CC'],
        borderColor:     ['#FF007F', '#00B29A', '#FFD700'],
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#3d0020' }, ticks: { color: '#9e8899' }, beginAtZero: true },
        y: { grid: { color: '#3d0020' }, ticks: { color: '#9e8899' } },
      },
    },
  });
}

// ============================================================
// Tables
// ============================================================
function renderGenreTable(genres) {
  const tbody = document.getElementById('table-genres');
  tbody.innerHTML = '';
  const max = genres.length ? Math.max(...genres.map(g => g.count)) : 1;
  genres.slice(0, 8).forEach((g, i) => {
    const pct = Math.round((g.count / max) * 100);
    tbody.innerHTML += `
      <tr>
        <td class="rank-col">${i + 1}</td>
        <td>${escHtml(g.genre)}</td>
        <td>${g.count.toLocaleString('pt-BR')}</td>
        <td>
          <div class="progress-bar-container">
            <div class="progress-bar">
              <div class="progress-bar-fill" style="width:${pct}%"></div>
            </div>
            <span class="progress-pct">${g.percentage}%</span>
          </div>
        </td>
      </tr>`;
  });
  if (!genres.length) tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Sem dados</td></tr>';
}

function renderTitlesTable(titles) {
  const tbody = document.getElementById('table-titles');
  tbody.innerHTML = '';
  titles.slice(0, 10).forEach((t, i) => {
    const typeLabel = t.content_type === 'movie' ? 'FILME' : 'SÉRIE';
    const typeCls   = t.content_type === 'movie' ? 'movie' : 'tv';
    const genres = t.genres
      ? t.genres.split('|').filter(Boolean).slice(0, 2).join(', ')
      : '—';
    tbody.innerHTML += `
      <tr>
        <td class="rank-col">${i + 1}</td>
        <td>${escHtml(t.title)}</td>
        <td><span class="result-type-badge ${typeCls}">${typeLabel}</span></td>
        <td class="text-muted">${escHtml(genres)}</td>
        <td>⭐ ${t.vote_avg.toFixed(1)}</td>
        <td class="text-primary font-bold">${t.recommendation_count}</td>
        <td class="font-mono">${t.avg_score.toFixed(1)}</td>
      </tr>`;
  });
  if (!titles.length) tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Sem dados</td></tr>';
}

// ============================================================
// Utility
// ============================================================
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
