import React, { useState } from 'react';
import { initialAssets } from './data/mockAssets';
import LiveFlightMap from './components/LiveFlightMap';
import FleetDashboard from './components/FleetDashboard';
import { 
  ShieldAlert, 
  Layers, 
  Map as MapIcon 
} from 'lucide-react';

export default function App() {
  const [assets, setAssets] = useState(initialAssets);
  const [selectedAsset, setSelectedAsset] = useState(assets[0]);
  const [activeTab, setActiveTab] = useState('map');
  const [showEmergencyAlert, setShowEmergencyAlert] = useState(false);

  const criticalCount = assets.filter(a => a.status === 'CRITICAL_ALERT').length;
  const warningCount = assets.filter(a => a.status === 'IDLE_WARNING').length;
  const activeCount = assets.filter(a => a.status === 'ACTIVE').length;

  const handleSelectAssetAndGoToMap = (asset) => {
    setSelectedAsset(asset);
    setActiveTab('map');
  };

  return (
    <div className="min-h-screen bg-[#0C0C0C] text-gray-100 flex flex-col font-sans selection:bg-[#FFCD11] selection:text-black">
      {/* Top Professional Caterpillar Header */}
      <header className="bg-[#141414] border-b border-[#242424] px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-4">
          <div className="bg-[#FFCD11] text-black font-black px-3.5 py-1.5 rounded-lg text-base tracking-widest flex items-center shadow-[0_0_15px_rgba(255,205,17,0.3)]">
            <span>CAT</span>
            <span className="text-[10px] font-black ml-2 uppercase bg-black text-[#FFCD11] px-1.5 py-0.5 rounded tracking-normal">
              PORTAL
            </span>
          </div>
          <div>
            <h1 className="text-sm font-extrabold text-white tracking-wide flex items-center">
              Smart Rental Tracking & Operations Hub
              <span className="ml-2 w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            </h1>
            <p className="text-[11px] text-neutral-400">
              Customer Telemetry Control System • Live Equipment Fleet Radar
            </p>
          </div>
        </div>

        {/* Global Live Stats */}
        <div className="hidden lg:flex items-center space-x-3 text-xs">
          <div className="flex items-center bg-[#1C1C1C] px-3.5 py-2 rounded-xl border border-[#2B2B2B]">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-2 shadow-[0_0_8px_#10B981]"></span>
            <span className="text-neutral-400 mr-1.5 font-medium">Active:</span>
            <span className="font-extrabold text-white">{activeCount}</span>
          </div>

          <div className="flex items-center bg-[#1C1C1C] px-3.5 py-2 rounded-xl border border-[#2B2B2B]">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 mr-2 shadow-[0_0_8px_#F59E0B]"></span>
            <span className="text-neutral-400 mr-1.5 font-medium">Idle Warning:</span>
            <span className="font-extrabold text-amber-400">{warningCount}</span>
          </div>

          <div className="flex items-center bg-[#1C1C1C] px-3.5 py-2 rounded-xl border border-[#2B2B2B]">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-2 animate-ping"></span>
            <span className="text-neutral-400 mr-1.5 font-medium">Anomalies:</span>
            <span className="font-extrabold text-rose-400">{criticalCount}</span>
          </div>

          <button 
            onClick={() => setShowEmergencyAlert(true)}
            className="flex items-center bg-red-950/60 hover:bg-red-900/80 border border-red-600/70 text-red-300 font-bold px-3.5 py-2 rounded-xl text-xs transition shadow-lg cursor-pointer"
          >
            <ShieldAlert className="w-4 h-4 mr-1.5 text-red-400" />
            Simulate Safety Lockout
          </button>
        </div>

        {/* View Switcher */}
        <div className="flex bg-[#1C1C1C] p-1 rounded-xl border border-[#2B2B2B] text-xs font-semibold">
          <button 
            onClick={() => setActiveTab('map')}
            className={`flex items-center px-4 py-2 rounded-lg transition ${
              activeTab === 'map' 
                ? 'bg-[#FFCD11] text-black font-extrabold shadow-md' 
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            <MapIcon className="w-3.5 h-3.5 mr-1.5" />
            Live Flightradar Map
          </button>
          <button 
            onClick={() => setActiveTab('fleet')}
            className={`flex items-center px-4 py-2 rounded-lg transition ${
              activeTab === 'fleet' 
                ? 'bg-[#FFCD11] text-black font-extrabold shadow-md' 
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5 mr-1.5" />
            Fleet Inventory & Usage
          </button>
        </div>
      </header>

      {/* Main Interactive Stage */}
      <main className="flex-1 p-4">
        {activeTab === 'map' ? (
          <LiveFlightMap 
            assets={assets} 
            selectedAsset={selectedAsset} 
            setSelectedAsset={setSelectedAsset} 
          />
        ) : (
          <FleetDashboard 
            assets={assets} 
            onSelectAsset={handleSelectAssetAndGoToMap}
            onOpenCheckInOut={() => alert('QR Check-In/Out Modal will open here in the next step!')}
          />
        )}
      </main>
    </div>
  );
}