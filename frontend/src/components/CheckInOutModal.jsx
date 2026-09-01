import React, { useState } from 'react';
import { 
  X, 
  QrCode, 
  ShieldCheck, 
  ArrowUpRight, 
  ArrowDownLeft, 
  Camera
} from 'lucide-react';

export default function CheckInOutModal({ isOpen, onClose, assets = [], onUpdateAsset }) {
  if (!isOpen) return null;

  const [mode, setMode] = useState('CHECK_OUT');
  const [selectedAssetId, setSelectedAssetId] = useState(assets[0]?.id || 'EQX1001');
  const [operatorId, setOperatorId] = useState('OP101');
  const [targetSiteId, setTargetSiteId] = useState('S003');
  const [qrScanned, setQrScanned] = useState(false);
  
  const [checklist, setChecklist] = useState({
    brakesAndSteering: false,
    fluidLevelsChecked: false,
    ppeComplianceConfirmed: false,
    emergencyStopTested: false
  });

  const selectedAsset = assets.find(a => a.id === selectedAssetId) || assets[0];
  const allChecklistPassed = Object.values(checklist).every(Boolean);

  const handleToggleChecklist = (key) => {
    setChecklist(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSimulateQRScan = () => {
    setQrScanned(true);
  };

  const handleSubmitTransaction = (e) => {
    e.preventDefault();
    if (mode === 'CHECK_OUT' && !allChecklistPassed) {
      alert('Safety Violation: All pre-operation inspection checks must be completed.');
      return;
    }

    if (onUpdateAsset && selectedAsset) {
      const updated = {
        ...selectedAsset,
        status: mode === 'CHECK_OUT' ? 'ACTIVE' : 'IDLE_WARNING',
        siteId: mode === 'CHECK_OUT' ? targetSiteId : null,
        siteName: mode === 'CHECK_OUT' ? `Site ${targetSiteId} Active Works` : 'Depot / In Transit',
        operatorId: mode === 'CHECK_OUT' ? operatorId : null,
        isAnomaly: false,
        anomaly: null
      };
      onUpdateAsset(updated);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
      <div className="bg-[#181818] border border-[#333333] w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden flex flex-col text-white font-sans">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#2B2B2B] flex items-center justify-between bg-[#141414]">
          <div className="flex items-center space-x-3">
            <div className="bg-[#FFCD11] p-2 rounded-xl text-black">
              <QrCode className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-white">
                Equipment Dispatch & Return Portal
              </h3>
              <p className="text-xs text-neutral-400">
                Digital QR Verification & Pre-Op Safety Checklist
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-neutral-400 hover:text-white p-1.5 rounded-lg hover:bg-neutral-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          <div className="grid grid-cols-2 gap-2 bg-[#111111] p-1 rounded-xl border border-[#2B2B2B]">
            <button
              type="button"
              onClick={() => setMode('CHECK_OUT')}
              className={`flex items-center justify-center py-2.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                mode === 'CHECK_OUT' 
                  ? 'bg-[#FFCD11] text-black shadow-md' 
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              <ArrowUpRight className="w-4 h-4 mr-1.5" />
              Check-Out (Dispatch)
            </button>
            <button
              type="button"
              onClick={() => setMode('CHECK_IN')}
              className={`flex items-center justify-center py-2.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                mode === 'CHECK_IN' 
                  ? 'bg-[#FFCD11] text-black shadow-md' 
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              <ArrowDownLeft className="w-4 h-4 mr-1.5" />
              Check-In (Return)
            </button>
          </div>

          <form onSubmit={handleSubmitTransaction} className="space-y-4 text-xs">
            <div>
              <label className="block text-neutral-400 font-semibold mb-1.5">
                Select Machinery ID
              </label>
              <select
                value={selectedAssetId}
                onChange={(e) => {
                  setSelectedAssetId(e.target.value);
                  setQrScanned(false);
                }}
                className="w-full bg-[#111111] border border-[#333333] rounded-xl px-3.5 py-2.5 text-white font-mono focus:outline-none focus:border-[#FFCD11]"
              >
                {assets.map(asset => (
                  <option key={asset.id} value={asset.id}>
                    {asset.id} — {asset.name} ({asset.type})
                  </option>
                ))}
              </select>
            </div>

            {/* QR Scanner Simulation */}
            <div className="bg-[#111111] border border-[#2B2B2B] rounded-xl p-3.5 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`p-2.5 rounded-lg ${qrScanned ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-600/40' : 'bg-neutral-800 text-neutral-400'}`}>
                  <Camera className="w-5 h-5" />
                </div>
                <div>
                  <div className="font-bold text-white">QR Machine Tag Verification</div>
                  <div className="text-[11px] text-neutral-400">
                    {qrScanned ? `✓ Verified Tag for ${selectedAssetId}` : 'Scan required before ignition'}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={handleSimulateQRScan}
                className={`px-3 py-1.5 rounded-lg font-bold text-xs transition cursor-pointer ${
                  qrScanned 
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                    : 'bg-[#FFCD11] hover:bg-[#E5B80E] text-black'
                }`}
              >
                {qrScanned ? 'Tag Verified' : 'Simulate Scan'}
              </button>
            </div>

            {mode === 'CHECK_OUT' && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-neutral-400 font-semibold mb-1.5">Operator ID</label>
                  <input
                    type="text"
                    value={operatorId}
                    onChange={(e) => setOperatorId(e.target.value)}
                    placeholder="e.g. OP101"
                    className="w-full bg-[#111111] border border-[#333333] rounded-xl px-3.5 py-2 text-white font-mono focus:outline-none focus:border-[#FFCD11]"
                    required
                  />
                </div>
                <div>
                  <label className="block text-neutral-400 font-semibold mb-1.5">Destination Site</label>
                  <select
                    value={targetSiteId}
                    onChange={(e) => setTargetSiteId(e.target.value)}
                    className="w-full bg-[#111111] border border-[#333333] rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-[#FFCD11]"
                  >
                    <option value="S001">S001 - Delhi Highway</option>
                    <option value="S002">S002 - Mumbai Coastal</option>
                    <option value="S003">S003 - Bangalore Quarry</option>
                    <option value="S006">S006 - Ahmedabad Hub</option>
                  </select>
                </div>
              </div>
            )}

            {mode === 'CHECK_OUT' && (
              <div className="bg-[#1F1912] border border-[#D97706]/40 rounded-xl p-3.5 space-y-2">
                <div className="flex items-center space-x-2 text-[#F59E0B] font-bold pb-1 border-b border-[#D97706]/20">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Mandatory Pre-Operation Checklist</span>
                </div>
                
                <div className="space-y-1.5 pt-1 text-neutral-300">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checklist.brakesAndSteering}
                      onChange={() => handleToggleChecklist('brakesAndSteering')}
                      className="w-3.5 h-3.5 accent-[#FFCD11] rounded"
                    />
                    <span>Hydraulics & Brakes Inspected</span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checklist.fluidLevelsChecked}
                      onChange={() => handleToggleChecklist('fluidLevelsChecked')}
                      className="w-3.5 h-3.5 accent-[#FFCD11] rounded"
                    />
                    <span>Engine Oil & Fuel Levels Verified</span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checklist.ppeComplianceConfirmed}
                      onChange={() => handleToggleChecklist('ppeComplianceConfirmed')}
                      className="w-3.5 h-3.5 accent-[#FFCD11] rounded"
                    />
                    <span>PPE & Safety Gear Compliant</span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checklist.emergencyStopTested}
                      onChange={() => handleToggleChecklist('emergencyStopTested')}
                      className="w-3.5 h-3.5 accent-[#FFCD11] rounded"
                    />
                    <span>Emergency Stop Switch Tested</span>
                  </label>
                </div>
              </div>
            )}

            <div className="pt-2">
              <button
                type="submit"
                className={`w-full py-2.5 rounded-xl font-black text-xs transition flex items-center justify-center cursor-pointer ${
                  mode === 'CHECK_OUT' && !allChecklistPassed
                    ? 'bg-neutral-800 text-neutral-500 cursor-not-allowed border border-neutral-700'
                    : 'bg-[#FFCD11] hover:bg-[#E5B80E] text-black'
                }`}
              >
                {mode === 'CHECK_OUT' ? 'Confirm Dispatch & Authorize Ignition' : 'Process Return & Check-In'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}