import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useFleet } from './hooks/useFleet';
import { useLiveSocket } from './hooks/useLiveSocket';
import FleetDashboard from './components/FleetDashboard';
import SafetyLockoutModal from './components/SafetyLockoutModal';
import CatLogo from './components/CatLogo';
import { 
  ShieldAlert, 
  Layers, 
  Map as MapIcon, 
  QrCode, 
  Building2, 
  AlertTriangle,
  BarChart3,
  Radio,
  HardHat
} from 'lucide-react';

const LiveFlightMap = React.lazy(() => import('./components/LiveFlightMap'));
const AnalyticsAndForecast = React.lazy(() => import('./components/AnalyticsAndForecast'));
const CheckInOutModal = React.lazy(() => import('./components/CheckInOutModal'));
const AssetQrSheet = React.lazy(() => import('./components/AssetQrSheet'));

export default function App() {
  const [isLiveStreaming, setIsLiveStreaming] = useState(true);
  const { assets, setAssets, sites, status: fleetStatus, error: fleetError, refetch } = useFleet({
    polling: isLiveStreaming,
  });

  const [selectedAsset, setSelectedAsset] = useState(null);
  const [activeTab, setActiveTab] = useState('fleet'); // 'fleet' | 'map' | 'analytics' | 'safety'
  const [selectedSiteFilter, setSelectedSiteFilter] = useState('ALL');
  const [showEmergencyAlert, setShowEmergencyAlert] = useState(false);
  const [violatedAsset, setViolatedAsset] = useState(null);
  const [isCheckInOutOpen, setIsCheckInOutOpen] = useState(false);
  const assetsRef = useRef(assets);

  useEffect(() => {
    assetsRef.current = assets;
  }, [assets]);

  // Set default selected asset on initial load
  //useEffect(() => {
  //  if (assets.length > 0 && !selectedAsset) {
   //   setSelectedAsset(assets[0]);
  //  }
  //}, [assets, selectedAsset]);

  // Automatic Lockout Watcher — only fires for assets the backend has actually
  // put into SAFETY_LOCKOUT (the state the override endpoint can clear).
  useEffect(() => {
    const lockedAsset = assets.find((a) => a.rawStatus === 'SAFETY_LOCKOUT');

    if (lockedAsset && !showEmergencyAlert && !sessionStorage.getItem('dismissed_' + lockedAsset.id)) {
      // The alert mirrors an external telemetry transition, so synchronizing local
      // dialog state here is intentional rather than derived render state.
      // eslint-disable-next-line react/set-state-in-effect
      setViolatedAsset(lockedAsset);
      setShowEmergencyAlert(true);
    }
  }, [assets, showEmergencyAlert]);

  const handleLockout = useCallback((msg) => {
    setViolatedAsset((prev) => {
      const found = assetsRef.current.find((a) => a.id === msg.asset_id);
      return found || prev || { id: msg.asset_id, name: msg.asset_id, anomaly: msg.reason };
    });
    setShowEmergencyAlert(true);
  }, []);

  const { connected: wsConnected } = useLiveSocket({
    enabled: isLiveStreaming,
    setAssets,
    onLockout: handleLockout,
  });

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
    <div className="flex min-h-dvh lg:h-dvh flex-col lg:flex-row bg-[#0C0C0C] text-gray-200 font-sans overflow-x-hidden lg:overflow-hidden">
      
      {/* 1. Left Navigation Sidebar */}
      <aside className="w-full lg:w-64 bg-[#121212] border-b lg:border-b-0 lg:border-r border-[#222] flex flex-col justify-between p-3 lg:p-4 shrink-0">
        <div className="space-y-3 lg:space-y-5">
          
          {/* Rebranded CATstats Header */}
          <div className="flex items-center space-x-3 px-1.5 py-1">
            <CatLogo className="h-8.5" />
            <div className="leading-tight">
              <div className="text-[14px] font-black text-white tracking-wider flex items-center">
                <span>CAT</span><span className="text-[#FFCD11]">stats</span>
              </div>
              <div className="text-[10px] text-neutral-400 font-medium">Smart Asset Operations</div>
            </div>
          </div>

          {/* Live Telemetry Stream Indicator */}
          <div className="bg-[#181818] border border-[#262626] rounded-xl p-2.5 flex items-center justify-between shadow-inner">
            <div className="flex items-center space-x-2">
              <Radio className={`w-3.5 h-3.5 ${isLiveStreaming && wsConnected ? 'text-emerald-400 animate-pulse' : isLiveStreaming ? 'text-amber-400' : 'text-neutral-500'}`} />
              <span className="text-[11px] font-semibold text-neutral-300">Telemetry Stream</span>
            </div>
            <button
              onClick={() => setIsLiveStreaming(!isLiveStreaming)}
              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase transition cursor-pointer ${
                isLiveStreaming ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-neutral-800 text-neutral-400'
              }`}
            >
              {isLiveStreaming ? 'Active' : 'Paused'}
            </button>
          </div>

          {/* Project Site Selector */}
          <div className="bg-[#181818] border border-[#262626] rounded-xl p-2.5">
            <label className="block text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-1.5 flex items-center">
              <Building2 className="w-3 h-3 mr-1 text-[#FFCD11]" />
              Project Site
            </label>
            <select
              value={selectedSiteFilter}
              onChange={(e) => setSelectedSiteFilter(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#FFCD11]"
            >
              <option value="ALL">All Active Sites (Fleet View)</option>
              {sites.map((s) => (
                <option key={s.site_id} value={s.site_id}>
                  {s.site_id} — {s.site_name || 'Site'}
                </option>
              ))}
            </select>
          </div>

          {/* Navigation Links */}
          <nav className="grid grid-cols-2 sm:grid-cols-5 lg:block gap-1 lg:space-y-1" aria-label="Primary navigation">
            <button
              onClick={() => setActiveTab('fleet')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'fleet'
                  ? 'bg-[#FFCD11] text-black font-bold shadow-md'
                  : 'text-neutral-400 hover:text-white hover:bg-[#181818]'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Layers className="w-4 h-4" />
                <span>Rented Assets</span>
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${activeTab === 'fleet' ? 'bg-black text-[#FFCD11]' : 'bg-[#222] text-neutral-400'}`}>
                {filteredAssetsBySite.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('map')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'map'
                  ? 'bg-[#FFCD11] text-black font-bold shadow-md'
                  : 'text-neutral-400 hover:text-white hover:bg-[#181818]'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <MapIcon className="w-4 h-4" />
                <span>Live Site Radar</span>
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            </button>

            <button
              onClick={() => setActiveTab('analytics')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'analytics'
                  ? 'bg-[#FFCD11] text-black font-bold shadow-md'
                  : 'text-neutral-400 hover:text-white hover:bg-[#181818]'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <BarChart3 className="w-4 h-4" />
                <span>Demand Forecast</span>
              </div>
              <span className="text-[10px] bg-[#FFCD11]/20 text-[#FFCD11] font-bold px-1.5 py-0.5 rounded">
                ARIMA
              </span>
            </button>

            <button
              onClick={() => setActiveTab('safety')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'safety'
                  ? 'bg-[#FFCD11] text-black font-bold shadow-md'
                  : 'text-neutral-400 hover:text-white hover:bg-[#181818]'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <ShieldAlert className="w-4 h-4" />
                <span>Safety Anomalies</span>
              </div>
              {criticalCount > 0 && (
                <span className="text-[10px] bg-rose-500 text-white font-bold px-1.5 py-0.5 rounded-full animate-bounce">
                  {criticalCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('qr')}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                activeTab === 'qr'
                  ? 'bg-[#FFCD11] text-black font-bold shadow-md'
                  : 'text-neutral-400 hover:text-white hover:bg-[#181818]'
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <QrCode className="w-4 h-4" />
                <span>Asset QR Codes</span>
              </div>
            </button>
          </nav>
        </div>

        {/* Sidebar Dispatch Action */}
        <div className="pt-3 border-t border-[#222]">
          <button
            onClick={() => setIsCheckInOutOpen(true)}
            className="w-full bg-[#FFCD11] hover:bg-[#E5B80E] text-black font-black py-2.5 rounded-xl text-xs flex items-center justify-center shadow-lg transition cursor-pointer"
          >
            <QrCode className="w-4 h-4 mr-2" />
            Scan Asset QR Tag
          </button>
        </div>
      </aside>

      {/* 2. Main Workstation Area */}
      <div className="min-w-0 flex-1 flex flex-col lg:overflow-y-auto">
        
        {/* Streamlined Clean Header */}
        <header className="bg-[#121212] border-b border-[#222] px-3 sm:px-6 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sticky top-0 z-30">
          <div className="flex items-center space-x-4">
            <div className="p-2 rounded-xl bg-[#1C1C1C] border border-[#282828] text-[#FFCD11]">
              <HardHat className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-sm font-bold text-white">Apex Infra Logistics Corp</h2>
                <span className="text-[10px] bg-[#222] text-neutral-400 px-2 py-0.5 rounded font-mono">Contract #CAT-2026-98</span>
              </div>
              <p className="text-[11px] text-neutral-400">
                Active Zone: <strong className="text-neutral-200">{selectedSiteFilter === 'ALL' ? 'All active sites' : sites.find((site) => site.site_id === selectedSiteFilter)?.site_name || selectedSiteFilter}</strong>
              </p>
            </div>
          </div>

          {/* Key Fleet KPI Badges */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="flex items-center space-x-1.5 bg-[#181818] border border-[#262626] px-3 py-1.5 rounded-xl text-neutral-300">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="text-[11px]">Active: <strong className="text-white">{activeCount}</strong></span>
            </div>
            <div className="flex items-center space-x-1.5 bg-[#181818] border border-[#262626] px-3 py-1.5 rounded-xl text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              <span className="text-[11px]">Idle: <strong className="text-white">{warningCount}</strong></span>
            </div>
            <div className="flex items-center space-x-1.5 bg-[#181818] border border-[#262626] px-3 py-1.5 rounded-xl text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
              <span className="text-[11px]">Hazards: <strong className="text-white">{criticalCount}</strong></span>
            </div>
          </div>
        </header>

        {fleetStatus === 'error' && (
          <div className="mx-6 mt-4 bg-rose-950/50 border border-rose-800/60 text-rose-200 text-xs rounded-xl px-4 py-2.5 flex items-center justify-between">
            <span>Cannot reach backend at {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'} — {fleetError?.message}</span>
            <button onClick={refetch} className="ml-3 bg-rose-800/60 hover:bg-rose-700 px-3 py-1 rounded-lg font-bold cursor-pointer">Retry</button>
          </div>
        )}
        {fleetStatus === 'loading' && (
          <div className="mx-6 mt-4 text-neutral-400 text-xs">Loading fleet…</div>
        )}

        {/* Active Tab Workspace */}
        <main className="p-3 sm:p-6 flex-1 flex flex-col">
          <React.Suspense fallback={<div className="p-6 text-xs text-neutral-400">Loading workspace…</div>}>
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
              activeSiteId={selectedSiteFilter === 'ALL' ? 'S003' : selectedSiteFilter}
            />
          )}

          {activeTab === 'analytics' && (
            <AnalyticsAndForecast assets={filteredAssetsBySite} />
          )}

          {activeTab === 'qr' && (
            <AssetQrSheet assets={assets} />
          )}

          {activeTab === 'safety' && (
            <div className="space-y-4">
              <div className="bg-[#141414] border border-[#242424] rounded-2xl p-5">
                <h3 className="text-sm font-bold text-white mb-1 flex items-center">
                  <ShieldAlert className="w-4 h-4 mr-2 text-rose-400" />
                  Live Safety Incidents & Sensor Anomalies
                </h3>
                <p className="text-xs text-neutral-400 mb-4">
                  Autonomous hazard flags (critical tilt angles, boundary breaches, and excessive shift idle waste).
                </p>

                <div className="space-y-3">
                  {assets.filter(a => a.isAnomaly || a.status === 'CRITICAL_ALERT').map(asset => (
                    <div key={asset.id} className="bg-[#181818] border border-[#282828] rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex items-center space-x-3">
                        <div className={`p-2.5 rounded-lg ${asset.status === 'CRITICAL_ALERT' ? 'bg-rose-950/60 text-rose-400 border border-rose-800/40' : 'bg-amber-950/60 text-amber-400 border border-amber-800/40'}`}>
                          <AlertTriangle className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-black text-[#FFCD11] font-mono">{asset.id}</span>
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
                        className="bg-neutral-800 hover:bg-neutral-700 text-neutral-200 px-3.5 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer"
                      >
                        Inspect Anomaly
                      </button>
                    </div>
                  ))}
                  {!assets.some(a => a.isAnomaly || a.status === 'CRITICAL_ALERT') && (
                    <div className="rounded-xl border border-emerald-900/50 bg-emerald-950/20 p-5 text-xs text-emerald-300">
                      No active safety anomalies. Live monitoring is running normally.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          </React.Suspense>
        </main>
      </div>

      {/* Modals */}
      <React.Suspense fallback={null}>
      {isCheckInOutOpen && <CheckInOutModal
        isOpen={isCheckInOutOpen}
        onClose={() => setIsCheckInOutOpen(false)}
        assets={assets}
        sites={sites}
        onUpdateAsset={handleUpdateAsset}
        onCommitted={refetch}
      />}
      </React.Suspense>

      {showEmergencyAlert && <SafetyLockoutModal
        isOpen={showEmergencyAlert}
        onClose={handleCloseSafetyModal}
        violatedAsset={violatedAsset}
        onCleared={refetch}
      />}
    </div>
  );
}
