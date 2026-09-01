import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  Lock,
  KeyRound,
  Radio,
  CheckCircle2,
  PhoneCall,
  FileWarning,
  X
} from 'lucide-react';

import { safetyOverride } from '../api/endpoints';

const DEMO_SUPERVISOR_ID = 'SUP-001'; // TODO: replace with real company login

export default function SafetyLockoutModal({ isOpen, onClose, violatedAsset, onCleared }) {
  if (!isOpen) return null;

  const [overridePin, setOverridePin] = useState('');
  const [supervisorId, setSupervisorId] = useState(DEMO_SUPERVISOR_ID);
  const [errorMessage, setErrorMessage] = useState('');
  const [resolutionNote, setResolutionNote] = useState('');
  const [isResolved, setIsResolved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleResolveAlert = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    const assetId = (violatedAsset && violatedAsset.id) || null;
    if (!assetId) {
      setErrorMessage('No asset context for this lockout.');
      return;
    }
    setSubmitting(true);
    try {
      await safetyOverride({
        asset_id: assetId,
        supervisor_id: supervisorId,
        pin: overridePin,
        resolution_note: resolutionNote,
        resume_status: 'ACTIVE',
      });
      setIsResolved(true);
      onCleared?.(assetId);
      setTimeout(() => {
        setIsResolved(false);
        setOverridePin('');
        setResolutionNote('');
        onClose();
      }, 1200);
    } catch (err) {
      if (err.status === 401) {
        setErrorMessage('Invalid supervisor ID or PIN.');
      } else if (err.status === 409) {
        setErrorMessage('This asset is not in a lockout state — nothing to override. You can close this dialog.');
      } else {
        setErrorMessage(err.message || 'Override failed');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const asset = violatedAsset || {
    id: "EQX1002",
    name: "Cat 777 Heavy Crane",
    tiltAngle: 34.8,
    speedKmH: 26.4
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/90 backdrop-blur-xl p-4">
      <div className="relative bg-[#161010] border-2 border-red-600 w-full max-w-xl rounded-2xl shadow-[0_0_50px_rgba(239,68,68,0.4)] overflow-hidden flex flex-col z-10 text-white font-sans">
        
        {/* Emergency Banner */}
        <div className="bg-red-600 px-6 py-4 flex items-center justify-between text-white">
          <div className="flex items-center space-x-3">
            <ShieldAlert className="w-7 h-7 animate-bounce" />
            <div>
              <h2 className="text-sm font-black tracking-widest uppercase">
                Critical Safety Violation Lockout
              </h2>
              <p className="text-[11px] font-semibold text-red-100">
                Machine Immobilized • Supervisor Override Required
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className="flex items-center bg-red-950 text-red-200 px-2.5 py-1 rounded-lg border border-red-800 text-[10px] font-mono font-bold">
              <Radio className="w-3 h-3 mr-1 animate-ping text-red-400" />
              LOCKED
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="p-1 rounded-lg bg-red-800/60 hover:bg-red-700 text-white transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="p-5 space-y-4 text-xs">
          {/* Diagnostic Stats */}
          <div className="bg-[#241414] border border-red-900/60 rounded-xl p-3.5 space-y-2.5">
            <div className="flex items-center justify-between border-b border-red-900/40 pb-2">
              <span className="font-mono font-bold text-[#FFCD11]">{asset.id} — {asset.name}</span>
              <span className="text-red-400 font-mono text-[10px]">#ALERT-TILT-902</span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="bg-[#180D0D] p-2 rounded-lg border border-red-900/40">
                <span className="text-[10px] text-neutral-400 block">Tilt / Roll</span>
                <span className="text-sm font-black text-red-400">{asset.tiltAngle || 34.8}° (Hazard)</span>
              </div>
              <div className="bg-[#180D0D] p-2 rounded-lg border border-red-900/40">
                <span className="text-[10px] text-neutral-400 block">Velocity</span>
                <span className="text-sm font-black text-amber-400">{asset.speedKmH || 24.5} km/h</span>
              </div>
              <div className="bg-[#180D0D] p-2 rounded-lg border border-red-900/40">
                <span className="text-[10px] text-neutral-400 block">Geofence</span>
                <span className="text-sm font-black text-rose-500">BREACHED</span>
              </div>
            </div>
          </div>

          {/* Form */}
          {isResolved ? (
            <div className="bg-emerald-950/60 border border-emerald-500 rounded-xl p-4 text-center text-emerald-300 flex flex-col items-center space-y-1">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
              <h3 className="text-sm font-bold">Safety Override Authorized</h3>
              <p className="text-[11px] text-emerald-200/80">Releasing interface lockout...</p>
            </div>
          ) : (
            <form onSubmit={handleResolveAlert} className="space-y-3">
              <div>
                <label className="block text-neutral-300 font-bold mb-1">
                  Supervisor Corrective Action Log
                </label>
                <input
                  type="text"
                  value={resolutionNote}
                  onChange={(e) => setResolutionNote(e.target.value)}
                  placeholder="e.g. Ground stabilized, machine inspected, site secure..."
                  required
                  className="w-full bg-[#111] border border-neutral-700 rounded-xl px-3 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-red-500"
                />
              </div>

              <div>
                <label className="block text-neutral-300 font-bold mb-1">Supervisor ID</label>
                <input
                  type="text"
                  value={supervisorId}
                  onChange={(e) => { setSupervisorId(e.target.value); setErrorMessage(''); }}
                  className="w-full bg-[#111] border border-neutral-700 rounded-xl px-3 py-2 text-white font-mono focus:outline-none focus:border-red-500"
                  required
                />
              </div>

              <div>
                <label className="block text-neutral-300 font-bold mb-1 flex items-center justify-between">
                  <span>Enter Authorization PIN to Unlock</span>
                  <span className="text-[10px] text-neutral-500 font-normal">demo: SUP-001 / 1234</span>
                </label>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-neutral-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    value={overridePin}
                    onChange={(e) => {
                      setOverridePin(e.target.value);
                      setErrorMessage('');
                    }}
                    placeholder="Enter PIN"
                    required
                    className="w-full bg-[#111] border border-neutral-700 rounded-xl pl-9 pr-3 py-2 text-white font-mono focus:outline-none focus:border-red-500"
                  />
                </div>
                {errorMessage && (
                  <p className="text-xs text-red-400 mt-1 font-semibold flex items-center">
                    <FileWarning className="w-3.5 h-3.5 mr-1" />
                    {errorMessage}
                  </p>
                )}
              </div>

              <div className="pt-2 flex items-center space-x-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full bg-red-600 hover:bg-red-500 disabled:bg-neutral-700 text-white font-black py-2.5 rounded-xl transition shadow-lg flex items-center justify-center cursor-pointer tracking-wider uppercase text-xs"
                >
                  <Lock className="w-4 h-4 mr-2" />
                  {submitting ? 'Authorizing…' : 'Authorize Override & Unlock'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}