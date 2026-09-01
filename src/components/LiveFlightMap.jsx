import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { 
  Gauge, 
  Fuel, 
  Radio, 
  AlertOctagon, 
  Clock, 
  Compass, 
  X,
  TrendingUp
} from 'lucide-react';
import { siteGeofences } from '../data/mockAssets';

// Custom Flightradar style Marker Icon
const createCustomIcon = (type, status, heading = 0) => {
  let color = '#10B981'; // Green (Active)
  if (status === 'IDLE_WARNING') color = '#F59E0B'; // Amber
  if (status === 'CRITICAL_ALERT') color = '#EF4444'; // Red

  const svgHtml = `
    <div style="transform: rotate(${heading}deg); display: flex; align-items: center; justify-content: center;">
      <div style="position: relative; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">
        <div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background: ${color}22; border: 1.5px solid ${color};"></div>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="${color}" stroke="#111" stroke-width="1.5">
          <polygon points="12 2 19 21 12 17 5 21 12 2"></polygon>
        </svg>
      </div>
    </div>
  `;

  return L.divIcon({
    html: svgHtml,
    className: 'custom-cat-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16]
  });
};

function MapRecenter({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords && coords.length === 2) {
      map.flyTo(coords, 13, { animate: true, duration: 1.0 });
    }
  }, [coords, map]);
  return null;
}

export default function LiveFlightMap({ assets = [], selectedAsset, setSelectedAsset }) {
  const defaultCenter = [20.5937, 78.9629]; // All-India View center

  return (
    <div className="relative w-full h-[82vh] rounded-xl overflow-hidden border border-[#2B2B2B] shadow-2xl bg-[#0F0F0F]">
      {/* Top Floating Mini-Radar Info Bar */}
      <div className="absolute top-4 left-4 z-[1000] bg-[#141414]/90 backdrop-blur-md border border-[#333333] px-4 py-2.5 rounded-xl shadow-2xl flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <Radio className="w-4 h-4 text-[#FFCD11] animate-pulse" />
          <span className="text-xs font-bold tracking-wider text-gray-200 uppercase">Live Telemetry Feed</span>
        </div>
        <div className="h-4 w-px bg-neutral-700"></div>
        <span className="text-xs text-neutral-400">
          Tracking: <strong className="text-white">{assets.length} Units</strong>
        </span>
      </div>

      {/* Main Map */}
      <MapContainer
        center={defaultCenter}
        zoom={5}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%', backgroundColor: '#0D0D0D' }}
      >
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {selectedAsset?.coords && <MapRecenter coords={selectedAsset.coords} />}

        {/* Site Geofence Circles */}
        {siteGeofences.map((site) => (
          <Circle
            key={site.siteId}
            center={site.center}
            radius={site.radius}
            pathOptions={{
              color: '#FFCD11',
              fillColor: '#FFCD11',
              fillOpacity: 0.1,
              weight: 1.5,
              dashArray: '4, 8'
            }}
          >
            <Popup>
              <div className="p-1 text-neutral-900">
                <p className="font-bold text-xs">{site.name}</p>
                <p className="text-[10px] text-neutral-600">ID: {site.siteId} • Radius: {site.radius}m</p>
              </div>
            </Popup>
          </Circle>
        ))}

        {/* Dynamic Trails */}
        {assets.map((asset) => (
          asset.trail && asset.trail.length > 1 && (
            <Polyline
              key={`trail-${asset.id}`}
              positions={asset.trail}
              pathOptions={{
                color: asset.status === 'CRITICAL_ALERT' ? '#EF4444' : '#10B981',
                weight: 2.5,
                opacity: 0.6,
                dashArray: '3, 6'
              }}
            />
          )
        ))}

        {/* Asset Markers */}
        {assets.map((asset) => (
          asset.coords && (
            <Marker
              key={asset.id}
              position={asset.coords}
              icon={createCustomIcon(asset.type, asset.status, asset.heading || 0)}
              eventHandlers={{
                click: () => setSelectedAsset(asset)
              }}
            >
              <Popup>
                <div className="p-1 text-neutral-900">
                  <span className="font-bold text-xs">{asset.id}</span>
                  <p className="text-xs">{asset.name}</p>
                </div>
              </Popup>
            </Marker>
          )
        ))}
      </MapContainer>

      {/* Slide-out Inspector Panel */}
      {selectedAsset && (
        <aside className="absolute top-4 right-4 bottom-4 w-88 z-[1000] bg-[#141414]/95 backdrop-blur-xl border border-[#2B2B2B] rounded-2xl shadow-2xl p-5 flex flex-col justify-between text-gray-100 overflow-y-auto">
          <div>
            <div className="flex items-start justify-between pb-3 border-b border-[#2B2B2B]">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-[#FFCD11] text-black font-mono">
                    {selectedAsset.id}
                  </span>
                  <span className="text-xs text-neutral-400 uppercase">{selectedAsset.type}</span>
                </div>
                <h3 className="text-sm font-extrabold text-white mt-1.5 leading-tight">
                  {selectedAsset.name}
                </h3>
                <p className="text-xs text-neutral-400 mt-0.5">
                  {selectedAsset.siteName || 'No Assigned Site'}
                </p>
              </div>
              <button 
                onClick={() => setSelectedAsset(null)}
                className="text-neutral-400 hover:text-white p-1 rounded-lg hover:bg-neutral-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {selectedAsset.isAnomaly && (
              <div className="mt-3 p-3 bg-red-950/40 border border-red-600/50 rounded-xl flex items-start space-x-2">
                <AlertOctagon className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-red-300">Anomaly Detected</h4>
                  <p className="text-[11px] text-red-200/90 mt-0.5">
                    {selectedAsset.anomaly || 'Operational pattern flagged by AI Engine'}
                  </p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2.5 mt-3 text-xs">
              <div className="bg-[#1C1C1C] p-2.5 rounded-xl border border-[#2B2B2B]">
                <div className="flex items-center text-neutral-400 mb-1">
                  <Gauge className="w-3.5 h-3.5 mr-1 text-[#FFCD11]" />
                  Engine
                </div>
                <div className="text-base font-black text-white">{selectedAsset.engineHours || 0} hrs</div>
              </div>

              <div className="bg-[#1C1C1C] p-2.5 rounded-xl border border-[#2B2B2B]">
                <div className="flex items-center text-neutral-400 mb-1">
                  <Clock className="w-3.5 h-3.5 mr-1 text-amber-400" />
                  Idle
                </div>
                <div className="text-base font-black text-amber-400">{selectedAsset.idleHours || 0} hrs</div>
              </div>

              <div className="bg-[#1C1C1C] p-2.5 rounded-xl border border-[#2B2B2B]">
                <div className="flex items-center text-neutral-400 mb-1">
                  <Fuel className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                  Fuel
                </div>
                <div className="text-base font-black text-emerald-400">{selectedAsset.fuelLevel || 0}%</div>
              </div>

              <div className="bg-[#1C1C1C] p-2.5 rounded-xl border border-[#2B2B2B]">
                <div className="flex items-center text-neutral-400 mb-1">
                  <Compass className="w-3.5 h-3.5 mr-1 text-cyan-400" />
                  Tilt
                </div>
                <div className="text-base font-black text-cyan-400">{selectedAsset.tiltAngle || 0}°</div>
              </div>
            </div>

            <div className="mt-3 bg-[#1C1C1C] p-3 rounded-xl border border-[#2B2B2B]">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-neutral-400 flex items-center">
                  <TrendingUp className="w-3.5 h-3.5 mr-1 text-purple-400" />
                  Service Health Cycle
                </span>
                <span className="font-bold text-neutral-200">{selectedAsset.hoursSinceMaintenance || 120} / 500 hrs</span>
              </div>
              <div className="w-full bg-neutral-800 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-emerald-500 to-purple-500 h-full rounded-full" 
                  style={{ width: `${Math.min(100, ((selectedAsset.hoursSinceMaintenance || 120) / 500) * 100)}%` }}
                ></div>
              </div>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}