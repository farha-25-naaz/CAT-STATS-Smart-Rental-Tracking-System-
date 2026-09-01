import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { 
  Gauge, 
  Battery, 
  Fuel, 
  Radio, 
  AlertOctagon, 
  Clock, 
  User, 
  Compass, 
  ShieldCheck, 
  X,
  TrendingUp
} from 'lucide-react';
import { siteGeofences } from '../data/mockAssets';

// Fix default Leaflet icon assets
delete L.Icon.Default.prototype._getIconUrl;

// Custom Flightradar style SVG Icon Generator
const createCustomIcon = (type, status, heading = 0) => {
  let color = '#10B981'; // Green (Active)
  if (status === 'IDLE_WARNING') color = '#F59E0B'; // Amber
  if (status === 'CRITICAL_ALERT') color = '#EF4444'; // Red

  const svgHtml = `
    <div style="transform: rotate(${heading}deg); transition: transform 0.4s ease; display: flex; align-items: center; justify-content: center;">
      <div style="position: relative; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">
        <div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background: ${color}22; border: 1.5px solid ${color}; ${status === 'CRITICAL_ALERT' ? 'animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;' : ''}"></div>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="${color}" stroke="#111" stroke-width="1.5">
          <polygon points="12 2 19 21 12 17 5 21 12 2"></polygon>
        </svg>
      </div>
    </div>
  `;

  return L.divIcon({
    html: svgHtml,
    className: 'custom-cat-marker',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18]
  });
};

// Map Recenter Helper
function MapRecenter({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords) {
      map.flyTo(coords, 14, { animate: true, duration: 1.2 });
    }
  }, [coords, map]);
  return null;
}

export default function LiveFlightMap({ assets, selectedAsset, setSelectedAsset }) {
  const defaultCenter = [20.5937, 78.9629]; // All-India View center

  return (
    <div className="relative w-full h-[calc(100vh-80px)] rounded-xl overflow-hidden border border-[#2B2B2B] shadow-2xl bg-[#0F0F0F]">
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
        <div className="h-4 w-px bg-neutral-700"></div>
        <span className="text-xs text-neutral-400">
          Mode: <strong className="text-[#FFCD11]">Direct Geostationary</strong>
        </span>
      </div>

      {/* Main Leaflet Map Engine */}
      <MapContainer
        center={defaultCenter}
        zoom={5}
        scrollWheelZoom={true}
        className="w-full h-full"
        style={{ background: '#0D0D0D' }}
      >
        {/* Dark CartoDB Tiles (Flightradar Dark Style) */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {selectedAsset && <MapRecenter coords={selectedAsset.coords} />}

        {/* Site Geofence Circles */}
        {siteGeofences.map((site) => (
          <Circle
            key={site.siteId}
            center={site.center}
            radius={site.radius}
            pathOptions={{
              color: '#FFCD11',
              fillColor: '#FFCD11',
              fillOpacity: 0.07,
              weight: 1.5,
              dashArray: '4, 8'
            }}
          >
            <Popup className="cat-custom-popup">
              <div className="p-2 text-neutral-900 font-sans">
                <p className="font-extrabold text-xs text-[#111]">{site.name}</p>
                <p className="text-[10px] text-neutral-600">ID: {site.siteId} • Radius: {site.radius}m</p>
              </div>
            </Popup>
          </Circle>
        ))}

        {/* Dynamic Trails (Breadcrumbs) */}
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
          <Marker
            key={asset.id}
            position={asset.coords}
            icon={createCustomIcon(asset.type, asset.status, asset.heading || 0)}
            eventHandlers={{
              click: () => setSelectedAsset(asset)
            }}
          >
            <Popup className="cat-custom-popup">
              <div className="p-2.5 text-neutral-900 font-sans">
                <div className="flex items-center justify-between pb-1 border-b border-neutral-200">
                  <span className="font-black text-xs text-neutral-900">{asset.id}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                    asset.status === 'CRITICAL_ALERT' ? 'bg-red-100 text-red-700' :
                    asset.status === 'IDLE_WARNING' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
                  }`}>
                    {asset.status}
                  </span>
                </div>
                <p className="text-xs font-semibold mt-1 text-neutral-800">{asset.name}</p>
                <p className="text-[11px] text-neutral-500">{asset.siteName || 'Unassigned'}</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Flightradar24-Style Slide-Out Telemetry Inspector Drawer */}
      {selectedAsset && (
        <aside className="absolute top-4 right-4 bottom-4 w-96 z-[1000] bg-[#141414]/95 backdrop-blur-xl border border-[#2B2B2B] rounded-2xl shadow-2xl p-5 flex flex-col justify-between text-gray-100 overflow-y-auto animate-in slide-in-from-right duration-300">
          <div>
            {/* Header */}
            <div className="flex items-start justify-between pb-4 border-b border-[#2B2B2B]">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-[#FFCD11] text-black">
                    {selectedAsset.id}
                  </span>
                  <span className="text-xs text-neutral-400 uppercase tracking-wider">{selectedAsset.type}</span>
                </div>
                <h3 className="text-base font-extrabold text-white mt-1.5 leading-tight">
                  {selectedAsset.name}
                </h3>
                <p className="text-xs text-neutral-400 mt-0.5 flex items-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#FFCD11] mr-1.5"></span>
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

            {/* Anomaly Badge If Active */}
            {selectedAsset.isAnomaly && (
              <div className="mt-4 p-3 bg-red-950/40 border border-red-600/50 rounded-xl flex items-start space-x-2.5">
                <AlertOctagon className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-red-300 uppercase tracking-wide">Operational Anomaly Detected</h4>
                  <p className="text-xs text-red-200/90 mt-0.5">
                    {selectedAsset.anomaly || 'Irregular usage pattern flagged by AI Engine'}
                  </p>
                </div>
              </div>
            )}

            {/* Live Telemetry Grid */}
            <div className="grid grid-cols-2 gap-3 mt-4">
              <div className="bg-[#1C1C1C] p-3 rounded-xl border border-[#2B2B2B]">
                <div className="flex items-center text-neutral-400 text-xs mb-1">
                  <Gauge className="w-3.5 h-3.5 mr-1.5 text-[#FFCD11]" />
                  Engine Runtime
                </div>
                <div className="text-lg font-black text-white">{selectedAsset.engineHours} <span className="text-xs font-normal text-neutral-400">hrs</span></div>
              </div>

              <div className="bg-[#1C1C1C] p-3 rounded-xl border border-[#2B2B2B]">
                <div className="flex items-center text-neutral-400 text-xs mb-1">
                  <Clock className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
                  Idle Total
                </div>
                <div className="text-lg font-black text-amber-400">{selectedAsset.idleHours} <span className="text-xs font-normal text-neutral-400">hrs</span></div>
              </div>

              <div className="bg-[#1C1C1C] p-3 rounded-xl border border-[#2B2B2B]">
                <div className="flex items-center text-neutral-400 text-xs mb-1">
                  <Fuel className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
                  Fuel Level
                </div>
                <div className="text-lg font-black text-emerald-400">{selectedAsset.fuelLevel}%</div>
              </div>

              <div className="bg-[#1C1C1C] p-3 rounded-xl border border-[#2B2B2B]">
                <div className="flex items-center text-neutral-400 text-xs mb-1">
                  <Compass className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
                  Tilt / Pitch
                </div>
                <div className="text-lg font-black text-cyan-400">{selectedAsset.tiltAngle}°</div>
              </div>
            </div>

            {/* Health & Maintenance Status */}
            <div className="mt-4 bg-[#1C1C1C] p-3.5 rounded-xl border border-[#2B2B2B]">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="text-neutral-400 flex items-center">
                  <TrendingUp className="w-3.5 h-3.5 mr-1.5 text-purple-400" />
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

          {/* Bottom Action Footer */}
          <div className="pt-4 border-t border-[#2B2B2B] flex flex-col space-y-2">
            <button 
              onClick={() => alert(`Initiating Diagnostics & Video Feed for ${selectedAsset.id}`)}
              className="w-full bg-[#FFCD11] hover:bg-[#E5B80E] text-black font-extrabold py-2.5 rounded-xl text-xs transition shadow-lg flex items-center justify-center cursor-pointer"
            >
              <Radio className="w-4 h-4 mr-2" />
              Stream Cockpit Telemetry
            </button>
          </div>
        </aside>
      )}
    </div>
  );
}