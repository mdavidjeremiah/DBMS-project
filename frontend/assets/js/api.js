// Cookie-based JWT auth against FastAPI backend.

export const API_URL = window.__HW_API_URL__ || '';
export const TOKEN_COOKIE = 'hw_access_token';

export function getToken() {
  const match = document.cookie
    .split(';')
    .map((c) => c.trim())
    .find((c) => c.startsWith(`${TOKEN_COOKIE}=`));
  return match ? decodeURIComponent(match.split('=')[1]) : null;
}

export async function apiRequest(path, init = {}) {
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json');
  if (path === '/sales' && String(init.method || 'GET').toUpperCase() === 'POST' && !headers.has('Idempotency-Key')) {
    const keyName = 'hw_pending_sale_key';
    let key = sessionStorage.getItem(keyName);
    if (!key) {
      key = crypto.randomUUID();
      sessionStorage.setItem(keyName, key);
    }
    headers.set('Idempotency-Key', key);
  }
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: 'no-store' });
  const body = await response.json().catch(() => null);
  if (response.status === 401 && !['/login', '/departments/public', '/health'].includes(path)) {
    clearAccessToken();
    if (window.location.pathname !== '/login.html') window.location.replace('/login.html');
  }
  if (!response.ok) throw new Error(body?.detail ?? `API request failed (${response.status})`);
  if (path === '/sales' && String(init.method || 'GET').toUpperCase() === 'POST') sessionStorage.removeItem('hw_pending_sale_key');
  return body;
}

export function setAccessToken(token) {
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(token)}; Path=/; SameSite=Lax; Max-Age=3600`;
}

export function clearAccessToken() {
  document.cookie = `${TOKEN_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export async function loadList(path) {
  try {
    return { data: await apiRequest(path), error: null };
  } catch (error) {
    return { data: [], error: error instanceof Error ? error.message : 'Unable to load data' };
  }
}
