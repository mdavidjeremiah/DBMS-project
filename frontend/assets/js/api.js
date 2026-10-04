// Cookie-based JWT auth against FastAPI backend.

export const API_URL = window.__HW_API_URL__ || '';

export async function apiRequest(path, init = {}) {
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json');
  if (['/sales', '/api/sales'].includes(path) && String(init.method || 'GET').toUpperCase() === 'POST' && !headers.has('Idempotency-Key')) {
    const keyName = 'hw_pending_sale_key';
    let key = sessionStorage.getItem(keyName);
    if (!key) {
      key = crypto.randomUUID();
      sessionStorage.setItem(keyName, key);
    }
    headers.set('Idempotency-Key', key);
  }
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: 'include', cache: 'no-store' });
  const body = await response.json().catch(() => null);
  if (response.status === 401 && !['/login', '/departments/public', '/health'].includes(path)) {
    if (window.location.pathname !== '/login.html') window.location.replace('/login.html');
  }
  if (!response.ok) throw new Error(body?.detail ?? `API request failed (${response.status})`);
  if (['/sales', '/api/sales'].includes(path) && String(init.method || 'GET').toUpperCase() === 'POST') sessionStorage.removeItem('hw_pending_sale_key');
  return body;
}

export async function loadList(path) {
  try {
    return { data: await apiRequest(path), error: null };
  } catch (error) {
    return { data: [], error: error instanceof Error ? error.message : 'Unable to load data' };
  }
}
