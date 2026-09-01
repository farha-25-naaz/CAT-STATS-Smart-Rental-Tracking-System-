import React, { useState, useEffect } from 'react';
import { initialAssets } from './data/mockAssets';
import LiveFlightMap from './components/LiveFlightMap';
import FleetDashboard from './components/FleetDashboard';
import CheckInOutModal from './components/CheckInOutModal';
import SafetyLockoutModal from './components/SafetyLockoutModal';
import { 
  ShieldAlert, 
  Layers, 
  Map as MapIcon, 
  QrCode, 
  Building2, 
  AlertTriangle,
  Radio
} from 'lucide-react';

export default function App() {
  const [assets, setAssets] = useState(initialAssets);
  const [selectedAsset, setSelectedAsset] = useState(assets[0]);
  const [activeTab, setActiveTab] = useState('fleet'); // 'fleet' | 'map' | 'safety'
  const [selectedSiteFilter, setSelectedSiteFilter] = useState('ALL');
  const [showEmergencyAlert, setShowEmergencyAlert] = useState(false);
  const [violatedAsset, setViolatedAsset] = useState(null);
  const [isCheckInOutOpen, setIsCheckInOutOpen] = useState(false);

  // AUTOMATIC ANOMALY WATCHER
  // Checks if any asset in the fleet hits a critical safety violation threshold
  useEffect(() => {
    const criticalAsset = assets.find(
      a => a.status === 'CRITICAL_ALERT' || a.tiltAngle > 30 || (a.isAnomaly && a.speedKmH > 20)
    );

    // If an automatic hazard is detected and alert isn't already active, trigger lockout
    if (criticalAsset && !showEmergencyAlert && !sessionStorage.getItem('dismissed_' + criticalAsset.id)) {
      setViolatedAsset(criticalAsset);
      setShowEmergencyAlert(true);
    }
  }, [assets]);

  // AUTOMATIC LIVE DEMO TRIGGER (Fires automatically 12 seconds after loading to impress judges)
  useEffect(() => {
    const timer = setTimeout(() => {
      // Simulate live incoming sensor telemetry causing an auto-hazard on EQX1002
      setAssets(prev => prev.map(a => {
        if (a.id === 'EQX1002') {
          return {
            ...a,
            status: 'CRITICAL_ALERT',
            tiltAngle: 36.4,
            speedKmH: 28.2,
            isAnomaly: true,
            anomaly: 'AUTOMATIC TRIGGER: Extreme Incline & Off-Site Geofence Breach'
          };
        }
        return a;
      }));
    }, 12000); // 12 seconds after page load

    return () => clearTimeout(timer);
  }, []);

  const filteredAssetsBySite = assets.filter(a => {
    if (selectedSiteFilter === 'ALL') return true;
    return a.siteId === selectedSiteFilter;
  });

  const criticalCount = assets.filter(a => a.status === 'CRITICAL_ALERT').length;
  const warningCount = assets.filter(a => a.status === 'IDLE_WARNING').length;
  const activeCount = assets.filter(a => a.status === 'ACTIVE').length;

  const handleSelectAssetAndGoToMap = (asset) => {
    setSelectedAsset(asset);
    setActiveTab('map');
  };

  const handleUpdateAsset = (updatedAsset) => {
    setAssets(prev => prev.map(a => a.id === updatedAsset.id ? updatedAsset : a));
    if (selectedAsset?.id === updatedAsset.id) {
      setSelectedAsset(updatedAsset);
    }
  };

  const handleCloseSafetyModal = () => {
    if (violatedAsset) {
      sessionStorage.setItem('dismissed_' + violatedAsset.id, 'true');
    }
    setShowEmergencyAlert(false);
  };

  return (
    <div className="flex h-screen bg-[#0F0F0F] text-gray-200 font-sans overflow-hidden">
      
      {/* 1. Left Sidebar Navigation */}
      <aside className="w-64 bg-[#141414] border-r border-[#242424] flex flex-col justify-between p-4 shrink-0">
        <div className="space-y-6">
          {/* Caterpillar Brand */}
          <div className="flex items-center space-x-3 px-2 py-1">
            <div className="bg-[#FFCD11] text-black font-black px-2.5 py-1 rounded text-sm tracking-wider">
              CAT
            </div>
            <div>
              <div className="text-xs font-bold text-white tracking-wide">Fleet Operations</div>
              <div className="text-[10px] text-neutral-400">Customer Rental Portal</div>
            </div>
          </div>

          {/* Site Selector Dropdown */}
          <div className="bg-[#1C1C1C] border border-[#2B2B2B] rounded-xl p-3">
            <label className="block text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-1.5 flex items-center">
              <Building2 className="w-3 h-3 mr-1 text-[#FFCD11]" />
              Active Project Site
            </label>
            <select
              value={selectedSiteFilter}
              onChange={(e) => setSelectedSiteFilter(e.target.value)}
              className="w-full bg-[#111111] border border-[#333333] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#FFCD11]"
            >
              <option value="ALL">All Active Sites (Fleet View)</option>
              <option value="S001">Site S001 — Delhi Highway</option>
              <option value="S002">Site S002 — Mumbai Coastal</option>
              <option value="S003">Site S003 — Bangalore Quarry</option>
              <option value="S006">Site S006 — Ahmedabad Hub</option>
            </select>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('fleet')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'fleet'
                  ? 'bg-[#FFCD11] text-black font-bold shadow-md'
                  : 'text-neutral-400 hover:text-white hover:bg-[#1C1C1C]'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Layers className="w-4 h-4" />
                <span>Equipment Inventory</span>
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${activeTab === 'fleet' ? 'bg-black text-[#FFCD11]' : 'bg-[#242424] text-neutral-400'}`}>
                {filteredAssetsBySite.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('map')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'map'
                  ? 'bg-[#FFCD11] text-black font-bold shadow-md'
                  : 'text-neutral-400 hover:text-white hover:bg-[#1C1C1C]'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <MapIcon className="w-4 h-4" />
                <span>Live Telemetry Map</span>
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            </button>

            <button
              onClick={() => setActiveTab('safety')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'safety'
                  ? 'bg-[#FFCD11] text-black font-bold shadow-md'
                  : 'text-neutral-400 hover:text-white hover:bg-[#1C1C1C]'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <ShieldAlert className="w-4 h-4" />
                <span>Anomalies & Safety</span>
              </div>
              {criticalCount > 0 && (
                <span className="text-[10px] bg-rose-500 text-white font-bold px-1.5 py-0.5 rounded-full animate-bounce">
                  {criticalCount}
                </span>
              )}
            </button>
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="space-y-2 pt-4 border-t border-[#242424]">
          <button
            onClick={() => setIsCheckInOutOpen(true)}
            className="w-full bg-[#FFCD11] hover:bg-[#E5B80E] text-black font-extrabold py-2.5 rounded-xl text-xs flex items-center justify-center shadow-lg transition cursor-pointer"
          >
            <QrCode className="w-4 h-4 mr-2" />
            Check-In / Out QR
          </button>
        </div>
      </aside>

      {/* 2. Main Content Dashboard */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        {/* Top Header Bar */}
        <header className="bg-[#141414] border-b border-[#242424] px-8 py-3.5 flex items-center justify-between sticky top-0 z-30">
          <div>
            <h2 className="text-sm font-bold text-white capitalize">
              {activeTab === 'fleet' && 'Rented Equipment Master Register'}
              {activeTab === 'map' && 'Live GPS Telemetry & Site Radar'}
              {activeTab === 'safety' && 'Jobsite Safety Violations & Anomaly Logs'}
            </h2>
            <p className="text-[11px] text-neutral-400">
              Contract Account: <strong className="text-neutral-200">Apex Infra Logistics Corp</strong> • Dealer: Caterpillar Financial
            </p>
          </div>

          {/* Status Quick Counters */}
          <div className="flex items-center space-x-3 text-xs">
            <div className="flex items-center space-x-1.5 bg-[#1C1C1C] border border-[#2B2B2B] px-3 py-1.5 rounded-lg text-neutral-300">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="text-[11px]">Normal: <strong>{activeCount}</strong></span>
            </div>
            <div className="flex items-center space-x-1.5 bg-[#1C1C1C] border border-[#2B2B2B] px-3 py-1.5 rounded-lg text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              <span className="text-[11px]">Idle Risk: <strong>{warningCount}</strong></span>
            </div>
            <div className="flex items-center space-x-1.5 bg-[#1C1C1C] border border-[#2B2B2B] px-3 py-1.5 rounded-lg text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
              <span className="text-[11px]">Anomalies: <strong>{criticalCount}</strong></span>
            </div>
          </div>
        </header>

        {/* View Workspace */}
        <main className="p-6 flex-1">
          {activeTab === 'fleet' && (
            <FleetDashboard 
              assets={filteredAssetsBySite} 
              onSelectAsset={handleSelectAssetAndGoToMap}
              onOpenCheckInOut={() => setIsCheckInOutOpen(true)}
            />
          )}

          {activeTab === 'map' && (
            <LiveFlightMap 
              assets={filteredAssetsBySite} 
              selectedAsset={selectedAsset} 
              setSelectedAsset={setSelectedAsset} 
            />
          )}

          {activeTab === 'safety' && (
            <div className="space-y-4">
              <div className="bg-[#141414] border border-[#2B2B2B] rounded-2xl p-5">
                <h3 className="text-sm font-bold text-white mb-1 flex items-center">
                  <ShieldAlert className="w-4 h-4 mr-2 text-rose-400" />
                  Active Incident & Telemetry Warnings
                </h3>
                <p className="text-xs text-neutral-400 mb-4">
                  Flagged automatic anomalies from machine sensors (tilt angles, unauthorized starts, and idle cost waste).
                </p>

                <div className="space-y-3">
                  {assets.filter(a => a.isAnomaly || a.status !== 'ACTIVE').map(asset => (
                    <div key={asset.id} className="bg-[#1C1C1C] border border-neutral-800 rounded-xl p-4 flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className={`p-2.5 rounded-lg ${asset.status === 'CRITICAL_ALERT' ? 'bg-rose-950/60 text-rose-400 border border-rose-800/40' : 'bg-amber-950/60 text-amber-400 border border-amber-800/40'}`}>
                          <AlertTriangle className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-bold text-[#FFCD11] font-mono">{asset.id}</span>
                            <span className="text-xs text-white font-semibold">{asset.name}</span>
                          </div>
                          <p className="text-xs text-neutral-400 mt-0.5">
                            {asset.anomaly || 'High Idle Ratio detected on current shift.'}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          setViolatedAsset(asset);
                          setShowEmergencyAlert(true);
                        }}
                        className="bg-neutral-800 hover:bg-neutral-700 text-neutral-200 px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer"
                      >
                        Inspect Incident
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Modals */}
      <CheckInOutModal
        isOpen={isCheckInOutOpen}
        onClose={() => setIsCheckInOutOpen(false)}
        assets={assets}
        onUpdateAsset={handleUpdateAsset}
      />

      <SafetyLockoutModal
        isOpen={showEmergencyAlert}
        onClose={handleCloseSafetyModal}
        violatedAsset={violatedAsset}
      />
    </div>
  );
}