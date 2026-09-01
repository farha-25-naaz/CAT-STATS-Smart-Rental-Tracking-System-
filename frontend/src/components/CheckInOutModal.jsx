import React, { useId, useState } from 'react';
import {
  X,
  QrCode,
  ShieldCheck,
  ArrowUpRight,
  ArrowDownLeft,
  Camera,
  CheckCircle2
} from 'lucide-react';
import { checkOutAsset, checkInAsset } from '../api/endpoints';
import QrScanner from './QrScanner';
import { useModalDialog } from '../hooks/useModalDialog';

// A tag encodes either the bare id ("EXC-101") or {"asset_id":"EXC-101"}.
function parseAssetCode(raw) {
  const text = (raw || '').trim();
  if (!text) return null;
  try {
    const obj = JSON.parse(text);
    if (obj && typeof obj === 'object' && obj.asset_id) return String(obj.asset_id).trim();
  } catch {
    /* not JSON — treat as a plain id */
  }
  return text;
}

export default function CheckInOutModal({ isOpen, onClose, assets = [], sites = [], onUpdateAsset, onCommitted }) {
  const [mode, setMode] = useState('CHECK_OUT');
  const [selectedAssetId, setSelectedAssetId] = useState(assets[0]?.id || '');
  const [operatorId, setOperatorId] = useState('OP-1001');
  const [targetSiteId, setTargetSiteId] = useState(sites[0]?.site_id || 'S001');
  const [returnDate, setReturnDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().slice(0, 10);
  });
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [qrScanned, setQrScanned] = useState(false);
  const [manualCode, setManualCode] = useState('');
  const [cameraOn, setCameraOn] = useState(false);
  const [scanNote, setScanNote] = useState('');
  
  const [checklist, setChecklist] = useState({
    brakesAndSteering: false,
    fluidLevelsChecked: false,
    ppeComplianceConfirmed: false,
    emergencyStopTested: false
  });
  const titleId = useId();
  const assetFieldId = useId();
  const operatorFieldId = useId();
  const siteFieldId = useId();
  const returnFieldId = useId();
  const dialogRef = useModalDialog({ isOpen, onClose });

  const selectedAsset = assets.find(a => a.id === selectedAssetId) || assets[0];
  const allChecklistPassed = Object.values(checklist).every(Boolean);

  // An asset can only be dispatched when it is currently UNASSIGNED, and can
  // only be returned when it is currently out (anything other than UNASSIGNED).
  const assetStatus = selectedAsset?.rawStatus;
  const canCheckOut = !selectedAsset || assetStatus === 'UNASSIGNED';
  const canCheckIn = !selectedAsset || assetStatus !== 'UNASSIGNED';
  const modeAllowed = mode === 'CHECK_OUT' ? canCheckOut : canCheckIn;
  const modeBlockReason = modeAllowed
    ? ''
    : mode === 'CHECK_OUT'
      ? `${selectedAsset?.id} is already out (${assetStatus}). It must be checked in first.`
      : `${selectedAsset?.id} is not currently checked out (${assetStatus}).`;

  const handleToggleChecklist = (key) => {
    setChecklist(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const resolveScannedCode = (raw) => {
    const id = parseAssetCode(raw);
    if (!id) {
      setScanNote('Could not read a code.');
      return;
    }
    const match = assets.find((a) => a.id === id);
    if (!match) {
      setQrScanned(false);
      setScanNote(`Asset "${id}" is not in the current fleet. Check the tag and try again.`);
      return;
    }
    setSelectedAssetId(id);
    setQrScanned(true);
    setCameraOn(false);
    // Auto-pick the transaction from the asset's current state.
    const nextMode = match.rawStatus === 'UNASSIGNED' ? 'CHECK_OUT' : 'CHECK_IN';
    setMode(nextMode);
    setScanNote(`Verified tag: ${id} — ${match.name}. ${nextMode === 'CHECK_OUT' ? 'Ready to dispatch.' : 'Ready to return.'}`);
  };

  const handleSubmitTransaction = async (e) => {
    e.preventDefault();
    setApiError(null);
    if (!modeAllowed) {
      setApiError(modeBlockReason);
      return;
    }
    if (mode === 'CHECK_OUT' && !allChecklistPassed) {
      setApiError('Safety Violation: complete all pre-operation inspection checks.');
      return;
    }
    if (!selectedAssetId) {
      setApiError('Select an asset.');
      return;
    }

    setSubmitting(true);
    try {
      if (mode === 'CHECK_OUT') {
        await checkOutAsset({
          asset_id: selectedAssetId,
          site_id: targetSiteId,
          operator_id: operatorId,
          check_in_date: new Date(`${returnDate}T12:00:00Z`).toISOString(),
        });
      } else {
        await checkInAsset({ asset_id: selectedAssetId });
      }

      if (onUpdateAsset && selectedAsset) {
        onUpdateAsset({
          ...selectedAsset,
          status: mode === 'CHECK_OUT' ? 'ACTIVE' : 'UNASSIGNED',
          rawStatus: mode === 'CHECK_OUT' ? 'ACTIVE' : 'UNASSIGNED',
          siteId: mode === 'CHECK_OUT' ? targetSiteId : null,
          operatorId: mode === 'CHECK_OUT' ? operatorId : null,
          isAnomaly: false,
          anomaly: null,
        });
      }
      onCommitted?.();
      onClose();
    } catch (err) {
      setApiError(err.message || 'Transaction failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center overflow-y-auto bg-black/80 backdrop-blur-md p-2 sm:p-4">
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} className="bg-[#181818] border border-[#333333] w-full max-w-xl max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] rounded-xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col text-white font-sans">
        
        {/* Header */}
        <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-[#2B2B2B] flex items-center justify-between bg-[#141414] shrink-0">
          <div className="flex items-center space-x-3">
            <div className="bg-[#FFCD11] p-2 rounded-xl text-black">
              <QrCode className="w-5 h-5" />
            </div>
            <div>
              <h3 id={titleId} className="text-sm font-extrabold text-white">
                Equipment Dispatch & Return Portal
              </h3>
              <p className="text-xs text-neutral-400">
                Digital QR Verification & Pre-Op Safety Checklist
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            aria-label="Close dispatch and return dialog"
            className="text-neutral-400 hover:text-white p-1.5 rounded-lg hover:bg-neutral-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="min-h-0 overflow-y-auto overscroll-contain p-3 sm:p-6 space-y-4 sm:space-y-5">
          <div className="grid grid-cols-2 gap-2 bg-[#111111] p-1 rounded-xl border border-[#2B2B2B]">
            <button
              type="button"
              onClick={() => { setMode('CHECK_OUT'); setApiError(null); }}
              disabled={!canCheckOut}
              className={`flex items-center justify-center py-2.5 rounded-lg text-xs font-bold transition ${
                !canCheckOut
                  ? 'text-neutral-600 cursor-not-allowed'
                  : mode === 'CHECK_OUT'
                    ? 'bg-[#FFCD11] text-black shadow-md cursor-pointer'
                    : 'text-neutral-400 hover:text-white cursor-pointer'
              }`}
            >
              <ArrowUpRight className="w-4 h-4 mr-1.5" />
              Check-Out (Dispatch)
            </button>
            <button
              type="button"
              onClick={() => { setMode('CHECK_IN'); setApiError(null); }}
              disabled={!canCheckIn}
              className={`flex items-center justify-center py-2.5 rounded-lg text-xs font-bold transition ${
                !canCheckIn
                  ? 'text-neutral-600 cursor-not-allowed'
                  : mode === 'CHECK_IN'
                    ? 'bg-[#FFCD11] text-black shadow-md cursor-pointer'
                    : 'text-neutral-400 hover:text-white cursor-pointer'
              }`}
            >
              <ArrowDownLeft className="w-4 h-4 mr-1.5" />
              Check-In (Return)
            </button>
          </div>

          {selectedAsset && (
            <div className="text-[11px] text-neutral-400 -mt-2">
              {selectedAsset.id} is currently <span className="font-bold text-neutral-200">{assetStatus}</span>
              {modeBlockReason && <span className="text-amber-400"> — {modeBlockReason}</span>}
            </div>
          )}

          <form onSubmit={handleSubmitTransaction} className="space-y-4 text-xs">
            <div>
              <label htmlFor={assetFieldId} className="block text-neutral-400 font-semibold mb-1.5">
                Select Machinery ID
              </label>
              <select
                id={assetFieldId}
                data-autofocus
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

            {/* QR machine-tag verification: camera scan, or type/paste the code */}
            <div className="bg-[#111111] border border-[#2B2B2B] rounded-xl p-3.5 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center space-x-3">
                  <div className={`p-2.5 rounded-lg ${qrScanned ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-600/40' : 'bg-neutral-800 text-neutral-400'}`}>
                    {qrScanned ? <CheckCircle2 className="w-5 h-5" /> : <Camera className="w-5 h-5" />}
                  </div>
                  <div>
                    <div className="font-bold text-white">QR Machine Tag Verification</div>
                    <div className="text-[11px] text-neutral-400">
                      {qrScanned ? `Verified tag for ${selectedAssetId}` : 'Scan the tag, or enter the code below'}
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => { setCameraOn((v) => !v); setScanNote(''); }}
                  className={`px-3 py-1.5 rounded-lg font-bold text-xs transition cursor-pointer ${
                    cameraOn ? 'bg-neutral-800 text-neutral-300 border border-neutral-600' : 'bg-[#FFCD11] hover:bg-[#E5B80E] text-black'
                  }`}
                >
                  {cameraOn ? 'Stop Camera' : 'Scan with Camera'}
                </button>
              </div>

              {cameraOn && (
                <QrScanner
                  onDecode={resolveScannedCode}
                  onError={() => setScanNote('No camera available — type or paste the asset code instead.')}
                />
              )}

              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="text"
                  value={manualCode}
                  onChange={(e) => setManualCode(e.target.value)}
                  placeholder="Enter asset code e.g. EXC-101"
                  className="min-w-0 flex-1 bg-[#0D0D0D] border border-[#333] rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-[#FFCD11]"
                />
                <button
                  type="button"
                  onClick={() => resolveScannedCode(manualCode)}
                  className="px-3 py-2 rounded-lg bg-[#1F1F1F] hover:bg-[#2A2A2A] border border-[#333] text-neutral-200 font-bold text-xs cursor-pointer"
                >
                  Use Code
                </button>
              </div>

              {scanNote && <div className="text-[11px] text-emerald-300/90">{scanNote}</div>}
            </div>

            {mode === 'CHECK_OUT' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor={operatorFieldId} className="block text-neutral-400 font-semibold mb-1.5">Operator ID</label>
                  <input
                    id={operatorFieldId}
                    type="text"
                    value={operatorId}
                    onChange={(e) => setOperatorId(e.target.value)}
                    placeholder="e.g. OP101"
                    className="w-full bg-[#111111] border border-[#333333] rounded-xl px-3.5 py-2 text-white font-mono focus:outline-none focus:border-[#FFCD11]"
                    required
                  />
                </div>
                <div>
                  <label htmlFor={siteFieldId} className="block text-neutral-400 font-semibold mb-1.5">Destination Site</label>
                  <select
                    id={siteFieldId}
                    value={targetSiteId}
                    onChange={(e) => setTargetSiteId(e.target.value)}
                    className="w-full bg-[#111111] border border-[#333333] rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-[#FFCD11]"
                  >
                    {(sites.length ? sites : [{ site_id: 'S001', site_name: 'Site S001' }]).map((s) => (
                      <option key={s.site_id} value={s.site_id}>
                        {s.site_id} — {s.site_name || 'Site'}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label htmlFor={returnFieldId} className="block text-neutral-400 font-semibold mb-1.5">Expected Return Date</label>
                  <input
                    id={returnFieldId}
                    type="date"
                    value={returnDate}
                    onChange={(e) => setReturnDate(e.target.value)}
                    className="w-full bg-[#111111] border border-[#333333] rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-[#FFCD11]"
                    required
                  />
                </div>
              </div>
            )}

            {apiError && (
              <div className="bg-rose-950/50 border border-rose-800/60 text-rose-200 text-[11px] rounded-lg px-3 py-2">
                {apiError}
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
                disabled={submitting || !modeAllowed || (mode === 'CHECK_OUT' && !allChecklistPassed)}
                className={`w-full py-2.5 rounded-xl font-black text-xs transition flex items-center justify-center ${
                  submitting || !modeAllowed || (mode === 'CHECK_OUT' && !allChecklistPassed)
                    ? 'bg-neutral-800 text-neutral-500 cursor-not-allowed border border-neutral-700'
                    : 'bg-[#FFCD11] hover:bg-[#E5B80E] text-black cursor-pointer'
                }`}
              >
                {submitting
                  ? 'Submitting…'
                  : mode === 'CHECK_OUT' ? 'Confirm Dispatch & Authorize Ignition' : 'Process Return & Check-In'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
