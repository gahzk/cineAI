/**
 * auth.js — Shared auth utilities used by all pages.
 * Initialises the navbar user info and handles logout.
 */

// Redirect to login if no token is present
function requireAuth() {
  if (!localStorage.getItem('cineai_token')) {
    window.location.href = '/login';
    return false;
  }
  return true;
}

// Populate navbar with the logged-in user's info
async function initNavbar() {
  const userEl = document.getElementById('navbar-username');
  const dashLink = document.getElementById('nav-dashboard');

  try {
    const user = await api.me();
    if (userEl) userEl.textContent = user.username;
    // Show dashboard link only for admins
    if (dashLink && user.is_admin) dashLink.style.display = '';
  } catch {
    // Token invalid — redirect handled inside api.request
  }

  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      localStorage.removeItem('cineai_token');
      window.location.href = '/login';
    });
  }
}

// Toast notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast alert-${type}`;
  toast.style.cssText = `
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 0.75rem 1.25rem;
    border-radius: 8px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.6);
    animation: slideIn 0.3s ease, fadeOut 0.4s ease 3.6s forwards;
    font-size: 0.88rem;
    font-weight: 500;
    pointer-events: auto;
    max-width: 340px;
  `;
  if (type === 'error') toast.style.borderColor = 'rgba(255,79,79,0.4)';
  if (type === 'success') toast.style.borderColor = 'rgba(0,210,106,0.4)';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
