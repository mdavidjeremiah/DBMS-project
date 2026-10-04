/**
 * Hardware World ERP — Notification Centre
 *
 * Manages toast notifications, bell-icon alerts, and critical banners.
 * Polls /api/approvals and /api/dashboard to surface live alerts.
 */

import { apiRequest } from './api.js?v=20261004-4';
import { can } from './permissions.js?v=20261004-4';

// ─── Toast Notifications ───────────────────────────────────────────

let _toastContainer = null;

function ensureToastContainer() {
  if (!_toastContainer) {
    _toastContainer = document.createElement('div');
    _toastContainer.id = 'hw-toast-container';
    _toastContainer.style.cssText = `
      position: fixed; bottom: 1.5rem; right: 1.5rem;
      z-index: 9999; display: flex; flex-direction: column; gap: 0.5rem;
      max-width: 22rem;
    `;
    document.body.appendChild(_toastContainer);
  }
  return _toastContainer;
}

/**
 * Show a toast notification.
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} type
 * @param {number} duration ms; 0 = persistent
 */
export function showToast(message, type = 'info', duration = 4000) {
  const container = ensureToastContainer();

  const colorMap = {
    success: 'var(--primary)',
    error: 'var(--destructive)',
    warning: 'var(--accent)',
    info: 'var(--steel)',
  };

  const iconMap = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
  };

  const toast = document.createElement('div');
  toast.style.cssText = `
    display: flex; align-items: flex-start; gap: 0.75rem;
    background: var(--card); border: 1px solid var(--border);
    border-left: 4px solid ${colorMap[type] || colorMap.info};
    border-radius: var(--radius); padding: 0.875rem 1rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    animation: hw-slide-in 0.2s ease-out;
    font-size: 0.875rem; color: var(--foreground);
  `;
  toast.innerHTML = `
    <span style="color:${colorMap[type]};font-weight:700;font-size:1rem;line-height:1.2;">${iconMap[type]}</span>
    <span style="flex:1">${message}</span>
    <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;color:var(--muted-foreground);line-height:1;font-size:1.1rem;">&times;</button>
  `;

  container.appendChild(toast);

  if (duration > 0) {
    setTimeout(() => toast.remove(), duration);
  }

  return toast;
}

// Convenience shortcuts
export const toast = {
  success: (msg, ms) => showToast(msg, 'success', ms),
  error: (msg, ms) => showToast(msg, 'error', ms || 6000),
  warning: (msg, ms) => showToast(msg, 'warning', ms),
  info: (msg, ms) => showToast(msg, 'info', ms),
};

// ─── Confirmation Dialog ───────────────────────────────────────────

/**
 * Show a modal confirmation dialog.
 * Returns a Promise<boolean> — true if confirmed, false if cancelled.
 * @param {string} title
 * @param {string} message
 * @param {string} confirmLabel
 * @param {'danger'|'primary'} variant
 */
export function confirm(title, message, confirmLabel = 'Confirm', variant = 'primary') {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position:fixed;inset:0;background:rgba(0,0,0,0.45);
      z-index:9998;display:flex;align-items:center;justify-content:center;
    `;

    const btnColor = variant === 'danger' ? 'var(--destructive)' : 'var(--primary)';
    overlay.innerHTML = `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
                  padding:2rem;max-width:28rem;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.2);">
        <h2 style="margin:0 0 0.5rem;font-size:1.125rem;">${title}</h2>
        <p style="color:var(--muted-foreground);margin:0 0 1.5rem;">${message}</p>
        <div style="display:flex;gap:0.75rem;justify-content:flex-end;">
          <button id="hw-cancel" style="padding:.5rem 1.25rem;border:1px solid var(--border);
            background:transparent;border-radius:var(--radius);cursor:pointer;color:var(--foreground);">
            Cancel
          </button>
          <button id="hw-confirm" style="padding:.5rem 1.25rem;background:${btnColor};
            color:#fff;border:none;border-radius:var(--radius);cursor:pointer;font-weight:600;">
            ${confirmLabel}
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    overlay.querySelector('#hw-cancel').addEventListener('click', () => { overlay.remove(); resolve(false); });
    overlay.querySelector('#hw-confirm').addEventListener('click', () => { overlay.remove(); resolve(true); });
    overlay.addEventListener('click', (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } });
  });
}

// ─── Alert Banner ──────────────────────────────────────────────────

/**
 * Render a dismissible critical-alert banner inside a container element.
 * @param {HTMLElement} container
 * @param {string} message
 * @param {'critical'|'warning'|'info'} level
 * @param {string|null} actionLabel
 * @param {Function|null} onAction
 */
export function renderAlertBanner(container, message, level = 'info', actionLabel = null, onAction = null) {
  const bg = { critical: '#fef2f2', warning: '#fffbeb', info: '#eff6ff' }[level] || '#eff6ff';
  const border = { critical: 'var(--destructive)', warning: 'var(--accent)', info: 'var(--steel)' }[level];
  const icon = { critical: '🔴', warning: '🟡', info: '🔵' }[level];

  const banner = document.createElement('div');
  banner.style.cssText = `
    background:${bg};border:1px solid ${border};border-radius:var(--radius);
    padding:.875rem 1rem;display:flex;align-items:center;gap:.75rem;
    margin-bottom:.75rem;font-size:.875rem;
  `;
  banner.innerHTML = `
    <span>${icon}</span>
    <span style="flex:1;color:var(--foreground);">${message}</span>
    ${actionLabel ? `<button id="alert-action" style="background:${border};color:#fff;border:none;
      border-radius:var(--radius);padding:.35rem .875rem;cursor:pointer;font-size:.8rem;font-weight:600;">
      ${actionLabel}</button>` : ''}
    <button onclick="this.parentElement.remove()"
      style="background:none;border:none;cursor:pointer;color:var(--muted-foreground);">&times;</button>
  `;
  if (actionLabel && onAction) {
    banner.querySelector('#alert-action')?.addEventListener('click', onAction);
  }
  container.prepend(banner);
}

// ─── Notification Bell (header badge) ─────────────────────────────

let _alertCount = 0;

export function updateNotificationBadge(count) {
  _alertCount = count;
  const badge = document.getElementById('hw-notif-badge');
  if (!badge) return;
  badge.textContent = count > 0 ? String(count > 99 ? '99+' : count) : '';
  badge.style.display = count > 0 ? 'inline-flex' : 'none';
}

/**
 * Fetch pending approvals and surface as badge + optional toasts.
 * Call once after login, then on a timer (e.g., every 2 min).
 */
export async function refreshAlerts() {
  if (!can('sales:view') && !can('inventory:view') && !can('procurement:requisition')) return;
  try {
    const approvals = await apiRequest('/api/approvals');
    if (Array.isArray(approvals)) {
      updateNotificationBadge(approvals.length);
    }
  } catch (_) {
    // Silent — badge stays as-is
  }
}
