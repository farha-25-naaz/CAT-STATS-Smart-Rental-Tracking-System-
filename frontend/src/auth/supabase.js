const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || '').replace(/\/$/, '');
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const SESSION_KEY = 'catstats_session';

export class AuthError extends Error {}

function ensureConfigured() {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new AuthError('Supabase login is not configured for this deployment.');
  }
}

async function supabaseRequest(path, { method = 'GET', body, token, prefer } = {}) {
  ensureConfigured();
  const response = await fetch(`${SUPABASE_URL}${path}`, {
    method,
    headers: {
      apikey: SUPABASE_ANON_KEY,
      Authorization: `Bearer ${token || SUPABASE_ANON_KEY}`,
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(prefer ? { Prefer: prefer } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!response.ok) {
    throw new AuthError(data?.msg || data?.message || data?.error_description || `Request failed (${response.status})`);
  }
  return data;
}

export async function signIn(email, password) {
  const session = await supabaseRequest('/auth/v1/token?grant_type=password', {
    method: 'POST',
    body: { email, password },
  });
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export async function refreshSession(refreshToken) {
  const session = await supabaseRequest('/auth/v1/token?grant_type=refresh_token', {
    method: 'POST',
    body: { refresh_token: refreshToken },
  });
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export async function getProfile(token, userId) {
  const rows = await supabaseRequest(`/rest/v1/profiles?id=eq.${encodeURIComponent(userId)}&select=id,email,full_name,role,organization_id,organizations(name)`, { token });
  if (!rows?.[0]) throw new AuthError('Your account has no CATstats profile. Ask an administrator to assign a role.');
  return { ...rows[0], organization_name: rows[0].organizations?.name || null };
}

export function loadStoredSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch { return null; }
}

export function clearStoredSession() {
  localStorage.removeItem(SESSION_KEY);
}

export const assetAdminApi = {
  list: (token) => supabaseRequest('/rest/v1/assets?select=*&order=asset_id.asc', { token }),
  update: (token, assetId, values) => supabaseRequest(`/rest/v1/assets?asset_id=eq.${encodeURIComponent(assetId)}`, {
    method: 'PATCH', body: values, token, prefer: 'return=representation',
  }),
};
