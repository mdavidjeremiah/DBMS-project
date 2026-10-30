// Cookie-based JWT auth against FastAPI backend.

export const API_URL = window.__HW_API_URL__ || '';

export async function apiRequest(path, init = {}) {
  const headers = new Headers(init.headers);
  if (
    !headers.has('Content-Type')
    && init.body
    && (typeof FormData === 'undefined' || !(init.body instanceof FormData))
  ) headers.set('Content-Type', 'application/json');
  const isSaleSubmission = ['/sales', '/api/sales'].includes(path)
    && String(init.method || 'GET').toUpperCase() === 'POST';
  if (isSaleSubmission && !headers.has('Idempotency-Key')) {
    const keyName = 'hw_pending_sale_key';
    let key = sessionStorage.getItem(keyName);
    const pendingBody = sessionStorage.getItem('hw_pending_sale_body');
    if (key && pendingBody && pendingBody !== init.body) throw new Error('A previous checkout is awaiting confirmation. Restore its original cart and retry before starting a different sale.');
    if (!key) {
      key = crypto.randomUUID();
      sessionStorage.setItem(keyName, key);
    }
    sessionStorage.setItem('hw_pending_sale_body', init.body);
    headers.set('Idempotency-Key', key);
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: init.credentials ?? 'include',
    cache: 'no-store',
  });
  const body = await response.json().catch(() => null);
  if (response.status === 401 && !['/login', '/departments/public', '/health'].includes(path)) {
    if (window.location.pathname !== '/login.html') window.location.replace('/login.html');
  }
  if (!response.ok) {
    const detail = Array.isArray(body?.detail) ? body.detail.map(e => `${e.loc?.slice(1).join('.') || 'Input'}: ${e.msg}`).join('; ') : body?.detail;
    if (isSaleSubmission && [400, 403, 404, 409, 422].includes(response.status)) {
      sessionStorage.removeItem('hw_pending_sale_key'); sessionStorage.removeItem('hw_pending_sale_body');
    }
    throw new Error(detail || `API request failed (${response.status})`);
  }
  if (isSaleSubmission) { sessionStorage.removeItem('hw_pending_sale_key'); sessionStorage.removeItem('hw_pending_sale_body'); }
  return body;
}

export async function loadList(path) {
  try {
    return { data: await apiRequest(path), error: null };
  } catch (error) {
    return { data: [], error: error instanceof Error ? error.message : 'Unable to load data' };
  }
}
