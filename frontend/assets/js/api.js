// Cookie-based JWT auth against FastAPI backend.

export const API_URL = window.__HW_API_URL__ || '';

export async function apiRequest(path, init = {}) {
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
    cache: 'no-store',
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `API request failed (${response.status})`);
  return body;
}

export async function loadList(path) {
  try {
    return { data: await apiRequest(path), error: null };
  } catch (error) {
    return { data: [], error: error instanceof Error ? error.message : 'Unable to load data' };
  }
}
