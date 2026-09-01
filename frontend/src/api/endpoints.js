import { api } from './client';

export const getLiveAssets = (opts) => api.get('/assets/live', opts);
export const getSites = (opts) => api.get('/sites', opts);
export const getOperators = (opts) => api.get('/operators', opts);

export const getUsageSummary = (assetId, days = 7, opts) =>
  api.get(`/usage-summary?asset_id=${encodeURIComponent(assetId)}&days=${days}`, opts);

export const getForecast = ({ siteId, equipmentType, horizon = 14 } = {}, opts) => {
  const q = new URLSearchParams();
  if (siteId) q.set('site_id', siteId);
  if (equipmentType) q.set('equipment_type', equipmentType);
  q.set('horizon', String(horizon));
  return api.get(`/forecast?${q.toString()}`, opts);
};

export const getAssetRisk = (assetId, opts) =>
  api.get(`/assets/${encodeURIComponent(assetId)}/risk`, opts);

export const generateAssetSummary = (assetId, opts) =>
  api.post(`/assets/${encodeURIComponent(assetId)}/generate-summary`, undefined, opts);

export const checkOutAsset = (body, opts) => api.post('/check-out', body, opts);
export const checkInAsset = (body, opts) => api.post('/check-in', body, opts);

export const safetyOverride = (body, opts) => api.post('/api/v1/safety/override', body, opts);
export const getActiveLockouts = (opts) => api.get('/api/v1/safety/active-lockouts', opts);

export const replayDemo = (body, opts) => api.post('/demo/replay', body, opts);
