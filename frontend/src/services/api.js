/* Thin fetch wrapper that attaches the Firebase ID token. */
import { useAuth } from './auth';

const API_BASE = import.meta.env.VITE_API_BASE || '';

export async function apiCall(path, opts = {}, token) {
  const res = await fetch(API_BASE + path, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {}),
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

export function useApi() {
  const { token } = useAuth();
  return {
    search: (keyword, topN = 10) => apiCall('/api/search', { method: 'POST', body: JSON.stringify({ keyword, topN }) }, token),
    analytics: (daysBack = 30) => apiCall(`/api/analytics?daysBack=${daysBack}`, {}, token),
    cagr: (category) => apiCall(`/api/cagr?category=${encodeURIComponent(category)}`, {}, token),
    yoy: (category) => apiCall(`/api/yoy?category=${encodeURIComponent(category)}`, {}, token),
    timeseries: (category) => apiCall(`/api/timeseries?category=${encodeURIComponent(category)}`, {}, token),
    favorites: () => apiCall('/api/favorites', {}, token),
    addFavorite: (keyword) => apiCall('/api/favorites', { method: 'POST', body: JSON.stringify({ keyword, frequency: 'weekly' }) }, token),
    removeFavorite: (keyword) => apiCall(`/api/favorites/${encodeURIComponent(keyword)}`, { method: 'DELETE' }, token),
    history: (daysBack = 7) => apiCall(`/api/search-history?daysBack=${daysBack}`, {}, token),
    compare: (brands, periodMonths = 12) => apiCall('/api/brand-compare', { method: 'POST', body: JSON.stringify({ brands, periodMonths }) }, token),
  };
}
