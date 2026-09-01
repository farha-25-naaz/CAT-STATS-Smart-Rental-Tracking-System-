import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Circle, Polyline, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { 
  Compass, 
  Fuel, 
  Clock, 
  AlertTriangle, 
  Activity, 
  ChevronRight, 
  Zap,
  X,
  Radio
} from 'lucide-react';

const BANGALORE_CENTER = [12.9716, 77.5946];

// Vector Machine Silhouettes
const getCleanMachineSvg = (type) => {
  const t = (type || '').toLowerCase();
  if (t.includes('excavator')) {
    return `<svg viewBox="0 0 24 24" width="24" height="24" fill="#FFCD11"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.6-.4-1-1-1h-2V7c0-1.1-.9-2-2-2H9c-1.1 0-2 .9-2 2v2H4c-.6 0-1 .4-1 1v7c0 .6.4 1 1 1h1c0 1.7 1.3 3 3 3s3-1.3 3-3h4c0 1.7 1.3 3 3 3s3-1.3 3-3zM7 18c-.6 0-1-.4-1-1s.4-1 1-1 1 .4 1 1-.4 1-1 1zm10 0c-.6 0-1-.4-1-1s.4-1 1-1 1 .4 1 1-.4 1-1 1zM9 7h8v5H9V7z"/></svg>`;
  }
  if (t.includes('bulldozer') || t.includes('dozer')) {
    return `<svg viewBox="0 0 24 24" width="24" height="24" fill="#FFCD11"><path d="M21 16.5c0 .8-.7 1.5-1.5 1.5h-15C3.7 18 3 17.3 3 16.5S3.7 15 4.5 15h15c.8 0 1.5.7 1.5 1.5zM18 9h-5V5h-3v4H4v4h14V9zM6 13h10v-2H6v2z"/></svg>`;
  }
  if (t.includes('crane')) {
    return `<svg viewBox="0 0 24 24" width="24" height="24" fill="#FFCD11"><path d="M21 20H3v-2h2V4h3l8 7h3v7h2v2zm-5-7l-6-5.2V18h6v-5z"/></svg>`;
  }
  return `<svg viewBox="0 0 24 24" width="24" height="24" fill="#FFCD11"><path d="M20 8h-3V4H3c-1.1 0-2 .9-2 2v11h2c0 1.7 1.3 3 3 3s3-1.3 3-3h6c0 1.7 1.3 3 3 3s3-1.3 3-3h2v-5l-3-4zM6 18.5c-.8 0-1.5-.7-1.5-1.5s.7-1.5 1.5-1.5 1.5.7 1.5 1.5-.7 1.5-1.5 1.5zm12 0c-.8 0-1.5-.7-1.5-1.5s.7-1.5 1.5-1.5 1.5.7 1.5 1.5-.7 1.5-1.5 1.5z"/></svg>`;
};

// Clean High-Contrast Marker
const createCleanMarkerIcon = (asset, isSelected) => {
  const statusColor = 
    asset.status === 'CRITICAL_ALERT' ? '#EF4444' : 
    asset.status === 'IDLE_WARNING' ? '#F59E0B' : '#10B981';

  const pulseRing = asset.status === 'CRITICAL_ALERT' 
    ? `<span style="position: absolute; inset: -4px; border-radius: 9999px; background-color: ${statusColor}; opacity: 0.8; animation: ping 1s cubic-bezier(0, 0, 0.2, 1) infinite;"></span>` 
    : '';

  const html = `
    <div style="display: flex; flex-direction: column; align-items: center; cursor: pointer; transform: ${isSelected ? 'scale(1.3)' : 'scale(1)'}; transition: transform 0.3s ease;">
      <!-- ID Badge -->
      <div style="background: rgba(15, 15, 15, 0.95); border: 1.5px solid ${isSelected ? '#FFCD11' : '#3E3E3E'}; color: ${isSelected ? '#FFCD11' : '#FFF'}; font-size: 10px; font-weight: 800; font-family: monospace; padding: 2px 6px; border-radius: 5px; margin-bottom: 3px; box-shadow: 0 4px 12px rgba(0,0,0,0.85); white-space: nowrap;">
        ${asset.id}
      </div>
      <!-- Machine Silhouette with Drop Shadow for Colorful Backgrounds -->
      <div style="position: relative; display: flex; align-items: center; justify-content: center; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.9)); background: rgba(0,0,0,0.4); padding: 3px; border-radius: 6px;">
        ${getCleanMachineSvg(asset.type)}
        <span style="position: absolute; bottom: 0px; right: 0px; width: 9px; height: 9px; border-radius: 9999px; background-color: ${statusColor}; border: 2px solid #000;">
          ${pulseRing}
        </span>
      </div>
    </div>
  `;

  return L.divIcon({
    className: 'clean-leaflet-marker',
    html: html,
    iconSize: [54, 58],
    iconAnchor: [27, 48]
  });
};

function MapController({ center }) {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
      if (center && Array.isArray(center) && center.length === 2) {
        map.flyTo(center, 14.5, { duration: 0.6 });
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [center, map]);
  return null;
}

function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click: () => onMapClick(),
  });
  return null;
}

export default function LiveFlightMap({ assets = [], selectedAsset, setSelectedAsset }) {
  const [mapCenter, setMapCenter] = useState(BANGALORE_CENTER);
  const [liveAssets, setLiveAssets] = useState([]);
  const [highlightCoords, setHighlightCoords] = useState(null);

  // Seed / re-sync from the real fleet. Only assets with a known position render.
  useEffect(() => {
    setLiveAssets((prev) => {
      const prevById = Object.fromEntries(prev.map((a) => [a.id, a]));
      return assets
        .filter((a) => Array.isArray(a.coords) && a.coords.length === 2)
        .map((a) => {
          const existing = prevById[a.id];
          return {
            ...a,
            productiveHours: a.engineHours,
            fuelPct: a.fuelLevel,
            healthScore: a.riskScore != null ? Math.round((1 - a.riskScore) * 100) : 92,
            // keep the locally accumulated trail across re-syncs
            trail: existing?.trail?.length ? [...existing.trail.slice(-11), a.coords] : [a.coords],
          };
        });
    });
  }, [assets]);

  // When an asset is picked elsewhere (e.g. the Rented Assets table), fly to it
  // and flash the locator ring once — no manual re-centre needed.
  useEffect(() => {
    if (!selectedAsset?.id) return undefined;
    const onMap = liveAssets.find((a) => a.id === selectedAsset.id);
    const target = onMap?.coords
      || (Array.isArray(selectedAsset.coords) ? selectedAsset.coords : null);
    if (!target) return undefined;

    setMapCenter(target);
    setHighlightCoords(target);
    const t = setTimeout(() => setHighlightCoords(null), 4000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAsset?.id]);

  // Gentle local motion so ACTIVE machines visibly move between backend frames.
  useEffect(() => {
    const interval = setInterval(() => {
      setLiveAssets(prevAssets =>
        prevAssets.map(asset => {
          if (asset.status !== 'ACTIVE' || !Array.isArray(asset.coords)) return asset;

          const deltaLat = (Math.random() - 0.5) * 0.0004;
          const deltaLng = (Math.random() - 0.5) * 0.0004;
          const newCoords = [asset.coords[0] + deltaLat, asset.coords[1] + deltaLng];
          const updatedTrail = [...(asset.trail || []), newCoords].slice(-8);

          return { ...asset, coords: newCoords, trail: updatedTrail };
        })
      );
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const activeSelected = liveAssets.find(a => a.id === selectedAsset?.id) || selectedAsset;

  const handleMarkerClick = (asset, e) => {
    L.DomEvent.stopPropagation(e);
    setSelectedAsset(asset);
    setMapCenter(asset.coords);
    setHighlightCoords(asset.coords);

    setTimeout(() => {
      setHighlightCoords(null);
    }, 4000);
  };

  const handleDeselect = () => {
    setSelectedAsset(null);
    setHighlightCoords(null);
  };

  return (
    <div className="flex-1 w-full h-[70dvh] lg:h-[calc(100vh-120px)] min-h-[420px] lg:min-h-[550px] relative rounded-2xl overflow-hidden border border-[#222] shadow-2xl">
      
      {/* Top HUD Tracker Pill */}
      <div className="absolute top-2 left-2 sm:top-4 sm:left-4 z-[1000] max-w-[calc(100%-1rem)] bg-[#121212]/90 backdrop-blur-md border border-[#2B2B2B] px-3 sm:px-4 py-2 rounded-xl flex flex-wrap items-center gap-2 sm:gap-3 shadow-2xl pointer-events-auto">
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-xs font-bold text-white tracking-wide">Live Site Radar</span>
        </div>
        <span className="text-neutral-500">|</span>
        <div className="flex items-center space-x-1 text-[11px] font-mono text-[#FFCD11]">
          <Radio className="w-3 h-3 animate-ping" />
          <span>{liveAssets.length} Active Units (2s Telemetry Loop)</span>
        </div>
      </div>

      {/* Map Container (Full Color Street-Level View) */}
      <MapContainer
        center={mapCenter}
        zoom={14}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
        attributionControl={false}
      >
        {/* Full-Color OpenStreetMap Tiles */}
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <MapController center={mapCenter} />
        <MapClickHandler onMapClick={handleDeselect} />

        {/* Temporary Asset Click Indicator Ring (Active for 4s) */}
        {highlightCoords && (
          <Circle
            center={highlightCoords}
            radius={250}
            pathOptions={{
              color: '#FFCD11',
              fillColor: '#FFCD11',
              fillOpacity: 0.25,
              weight: 2.5,
              dashArray: '4, 4'
            }}
          />
        )}

        {/* Dynamic Machines & Movement Trails */}
        {liveAssets.map((asset) => {
          const isSelected = activeSelected?.id === asset.id;
          return (
            <React.Fragment key={asset.id}>
              {/* Machine Movement Trail */}
              {asset.trail && asset.trail.length > 1 && (
                <Polyline
                  positions={asset.trail}
                  pathOptions={{
                    color: isSelected ? '#111111' : '#E5B80E',
                    weight: isSelected ? 4 : 2.5,
                    opacity: isSelected ? 1 : 0.7,
                    dashArray: '4, 4'
                  }}
                />
              )}

              {/* Machinery Marker */}
              <Marker
                position={asset.coords}
                icon={createCleanMarkerIcon(asset, isSelected)}
                eventHandlers={{
                  click: (e) => handleMarkerClick(asset, e),
                }}
              />
            </React.Fragment>
          );
        })}
      </MapContainer>

      {/* Slide-In Telemetry Drawer from Right Edge */}
      <div 
        className={`absolute inset-x-2 bottom-2 sm:inset-x-auto sm:bottom-auto sm:top-4 sm:right-4 z-[1001] sm:w-84 max-h-[calc(100%-5rem)] overflow-y-auto bg-[#141414]/95 backdrop-blur-xl border border-[#2B2B2B] rounded-2xl p-3 sm:p-5 shadow-2xl transition-all duration-300 transform ${
          activeSelected ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0 pointer-events-none'
        }`}
      >
        {activeSelected && (
          <div className="space-y-4">
            
            {/* Header with Close Button */}
            <div className="flex items-center justify-between border-b border-[#242424] pb-3">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded bg-[#FFCD11]/15 text-[#FFCD11] text-[11px] font-black font-mono">
                    {activeSelected.id}
                  </span>
                  <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                    activeSelected.status === 'CRITICAL_ALERT' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' :
                    activeSelected.status === 'IDLE_WARNING' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' :
                    'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  }`}>
                    {activeSelected.status}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-white mt-1">{activeSelected.name}</h3>
                <p className="text-[11px] text-neutral-400">Assigned: Bangalore Metro & Quarry Hub</p>
              </div>

              <button
                onClick={handleDeselect}
                className="p-1.5 rounded-lg bg-[#222] hover:bg-[#333] text-neutral-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-2.5">
              <div className="bg-[#1C1C1C] border border-[#282828] p-2.5 rounded-xl">
                <div className="flex items-center space-x-1.5 text-neutral-400 text-[10px] uppercase font-bold mb-1">
                  <Clock className="w-3 h-3 text-[#FFCD11]" />
                  <span>Work / Idle</span>
                </div>
                <div className="text-xs font-mono font-bold text-white">
                  {activeSelected.productiveHours ?? '—'}h <span className="text-neutral-500 font-normal">/</span> <span className="text-amber-400">{activeSelected.idleHours ?? '—'}h</span>
                </div>
              </div>

              <div className="bg-[#1C1C1C] border border-[#282828] p-2.5 rounded-xl">
                <div className="flex items-center space-x-1.5 text-neutral-400 text-[10px] uppercase font-bold mb-1">
                  <Fuel className="w-3 h-3 text-[#FFCD11]" />
                  <span>Fuel Level</span>
                </div>
                <div className="text-xs font-mono font-bold text-white">
                  {activeSelected.fuelPct ?? '—'}%
                </div>
              </div>

              <div className="bg-[#1C1C1C] border border-[#282828] p-2.5 rounded-xl">
                <div className="flex items-center space-x-1.5 text-neutral-400 text-[10px] uppercase font-bold mb-1">
                  <Compass className="w-3 h-3 text-[#FFCD11]" />
                  <span>Tilt Angle</span>
                </div>
                <div className={`text-xs font-mono font-bold ${(activeSelected.tiltAngle || 4.5) > 25 ? 'text-rose-400' : 'text-white'}`}>
                  {activeSelected.tiltAngle || 4.5}°
                </div>
              </div>

              <div className="bg-[#1C1C1C] border border-[#282828] p-2.5 rounded-xl">
                <div className="flex items-center space-x-1.5 text-neutral-400 text-[10px] uppercase font-bold mb-1">
                  <Activity className="w-3 h-3 text-[#FFCD11]" />
                  <span>Live Speed</span>
                </div>
                <div className="text-xs font-mono font-bold text-white">
                  {activeSelected.speedKmH || 14} km/h
                </div>
              </div>
            </div>

            {/* Component Health Progress Bar */}
            <div className="bg-[#1C1C1C] border border-[#282828] p-3 rounded-xl space-y-2">
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-neutral-300 font-semibold flex items-center">
                  <Zap className="w-3 h-3 mr-1 text-[#FFCD11]" /> Machine Health
                </span>
                <span className="font-mono font-bold text-[#FFCD11]">{activeSelected.healthScore || 94}%</span>
              </div>
              <div className="w-full bg-[#111] h-1.5 rounded-full overflow-hidden">
                <div 
                  className="bg-[#FFCD11] h-full rounded-full transition-all duration-500" 
                  style={{ width: `${activeSelected.healthScore || 94}%` }}
                ></div>
              </div>
            </div>

            {/* Active Hazard Warning */}
            {activeSelected.isAnomaly && (
              <div className="bg-rose-950/40 border border-rose-800/50 p-3 rounded-xl flex items-start space-x-2.5 text-rose-300 text-xs">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                <div>
                  <div className="font-bold text-rose-200">Active Warning</div>
                  <p className="text-[11px] text-rose-300/80 mt-0.5">{activeSelected.anomaly}</p>
                </div>
              </div>
            )}

            <button
              onClick={() => setMapCenter(activeSelected.coords)}
              className="w-full bg-[#1F1F1F] hover:bg-[#282828] text-neutral-200 border border-[#333] py-2 rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1 cursor-pointer"
            >
              <span>Re-center on Radar</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
