/**
 * Hardware World ERP — Frontend Permission Helper
 *
 * Provides utilities to check permissions from the /users/me response.
 * The backend is the authoritative source; this is a UI-layer convenience
 * to show/hide elements and redirect. It does NOT replace backend checks.
 */

/** @type {{ roletype: string, permissions: string[], roles: string[], departmentid: number, department_name: string, branchid: number, branch_name: string, employeeid: number, name: string } | null} */
let _currentUser = null;

/** Store the resolved user profile (call once after /users/me). */
export function setCurrentUser(user) {
  _currentUser = user;
  window.__HW_USER__ = user;
}

/** Get cached user. Returns null if not authenticated. */
export function getCurrentUser() {
  return _currentUser || window.__HW_USER__ || null;
}

/**
 * Check if the user has a given permission code.
 * Admin wildcard ("*") always passes.
 * @param {string} code  e.g. "sales:pos", "payroll:view"
 */
export function can(code) {
  const u = getCurrentUser();
  if (!u) return false;
  const perms = u.permissions || [];
  return perms.includes('*') || perms.includes(code);
}

/** Check multiple permissions — passes if the user has ANY one of them. */
export function canAny(...codes) {
  return codes.some((c) => can(c));
}

/** Check multiple permissions — passes only if the user has ALL of them. */
export function canAll(...codes) {
  return codes.every((c) => can(c));
}

/** True if the user's primary roletype matches any of the supplied values. */
export function hasRole(...roleNames) {
  const u = getCurrentUser();
  if (!u) return false;
  return roleNames.some(
    (r) => r.toLowerCase() === (u.roletype || '').toLowerCase()
  );
}

/** True if any of the user's assigned roles[] matches. */
export function hasAssignedRole(...roleNames) {
  const u = getCurrentUser();
  if (!u) return false;
  const lower = (u.roles || []).map((r) => r.toLowerCase());
  return roleNames.some((r) => lower.includes(r.toLowerCase()));
}

/** Return the routing dashboard key for the current role. */
export function defaultDashboard() {
  const u = getCurrentUser();
  if (!u) return 'login';
  const role = (u.roletype || '').toLowerCase().replace(/\s+/g, '_');
  const map = {
    admin: 'admin',
    cashier: 'sales',
    accountant: 'finance',
    hr_staff: 'hr',
    branch_manager: 'operations',
    procurement_officer: 'procurement',
  };
  return map[role] || 'admin';
}

/**
 * Hide or disable an element if the user lacks the required permission.
 * Usage: guardElement(document.getElementById('refund-btn'), 'sales:refund');
 * @param {HTMLElement|null} el
 * @param {string} code
 * @param {'hide'|'disable'} mode
 */
export function guardElement(el, code, mode = 'hide') {
  if (!el) return;
  if (!can(code)) {
    if (mode === 'disable') {
      el.disabled = true;
      el.title = 'You do not have permission for this action.';
    } else {
      el.style.display = 'none';
    }
  }
}

/**
 * Render an element only if user has permission; otherwise inject a
 * permission-denied placeholder inline.
 * @param {HTMLElement|null} container
 * @param {string} code
 * @param {string} html  HTML to render when permitted
 */
export function renderIfAllowed(container, code, html) {
  if (!container) return;
  if (can(code)) {
    container.innerHTML = html;
  } else {
    container.innerHTML = `
      <div class="card empty-state" style="text-align:center;padding:2rem;">
        <div style="font-size:2rem;margin-bottom:.5rem;">🔒</div>
        <p class="muted">You do not have permission to view this section.</p>
      </div>`;
  }
}
