// Adapts backend payloads (snake_case, backend status vocab) to the shape the
// existing UI components expect (camelCase, ACTIVE | IDLE_WARNING | CRITICAL_ALERT).

const MODEL_NAME_BY_TYPE = {
  Excavator: 'Cat 320 Hydraulic Excavator',
  Crane: 'Cat 777 Heavy Crane',
  Bulldozer: 'Cat D6 Track Bulldozer',
  Loader: 'Cat 950 Wheel Loader',
  'Dump Truck': 'Cat 730 Articulated Dump Truck',
  Grader: 'Cat 140 Motor Grader',
};

export function friendlyName(type, assetId) {
  return MODEL_NAME_BY_TYPE[type] || `${type || 'Asset'} ${assetId}`;
}

// backend status -> UI status bucket
export function toUiStatus(raw, { isAnomaly } = {}) {
  if (raw === 'SAFETY_LOCKOUT') return 'CRITICAL_ALERT';
  if (isAnomaly) return 'CRITICAL_ALERT';
  if (raw === 'ACTIVE') return 'ACTIVE';
  // IDLE, OVERDUE, UNASSIGNED and anything else fall here
  return 'IDLE_WARNING';
}

export function normalizeAsset(a, sitesById = {}) {
  const site = sitesById[a.current_site_id] || {};
  const hasCoords = a.lat != null && a.lng != null;
  const coords = hasCoords
    ? [a.lat, a.lng]
    : site.center_lat != null
      ? [site.center_lat, site.center_lng]
      : null;

  const severity = a.latest_anomaly_severity;
  const isAnomaly = Boolean(a.is_anomaly) || severity === 'HIGH' || severity === 'CRITICAL';
  const anomalyText = a.latest_anomaly_reason || a.latest_anomaly_type || null;

  return {
    id: a.asset_id,
    name: friendlyName(a.type, a.asset_id),
    type: a.type,
    siteId: a.current_site_id || null,
    siteName: a.site_name || site.site_name || null,
    operatorId: a.current_operator_id || null,
    status: toUiStatus(a.status, { isAnomaly }),
    rawStatus: a.status,
    checkOutDate: a.check_out_date ? a.check_out_date.slice(0, 10) : null,
    checkInDate: a.check_in_date ? a.check_in_date.slice(0, 10) : null,
    engineHours: a.engine_hours ?? 0,
    idleHours: a.idle_hours ?? 0,
    fuelLevel: a.fuel_level_pct ?? null,
    tiltAngle: a.tilt_angle_deg ?? 0,
    speedKmH: a.speed_kmh ?? 0,
    coords,
    trail: coords ? [coords] : [],
    isAnomaly,
    anomaly: anomalyText,
    riskTier: a.risk_tier || null,
    riskScore: a.risk_score ?? null,
    rentalRatePerDay: a.rental_rate_per_day ?? null,
    idleCostPerHour: a.idle_cost_per_hour ?? null,
    recordedAt: a.recorded_at || null,
  };
}

export function normalizeFleet(assets = [], sites = []) {
  const sitesById = Object.fromEntries(sites.map((s) => [s.site_id, s]));
  return assets.map((a) => normalizeAsset(a, sitesById));
}

// Merge a live telemetry WS frame into an existing normalized asset.
export function applyTelemetryFrame(asset, frame) {
  const next = { ...asset };
  if (frame.lat != null && frame.lng != null) {
    next.coords = [frame.lat, frame.lng];
    next.trail = [...(asset.trail || []), next.coords].slice(-12);
  }
  if (frame.speed_kmh != null) next.speedKmH = frame.speed_kmh;
  if (frame.tilt_angle != null) next.tiltAngle = frame.tilt_angle;
  if (frame.tilt_angle_deg != null) next.tiltAngle = frame.tilt_angle_deg;
  if (frame.engine_hours != null) next.engineHours = frame.engine_hours;
  if (frame.idle_hours != null) next.idleHours = frame.idle_hours;
  if (frame.fuel_level_pct != null) next.fuelLevel = frame.fuel_level_pct;
  if (frame.is_geofence_breach) {
    next.isAnomaly = true;
    next.anomaly = next.anomaly || 'Geofence breach detected';
  }
  return next;
}
