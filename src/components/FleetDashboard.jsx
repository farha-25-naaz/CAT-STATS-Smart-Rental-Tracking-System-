import React, { useState } from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Search, 
  Filter, 
  QrCode, 
  ArrowUpRight, 
  ArrowDownLeft, 
  ShieldAlert, 
  Activity, 
  DollarSign, 
  Calendar 
} from 'lucide-react';

export default function FleetDashboard({ assets, onSelectAsset, onOpenCheckInOut }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');

  // Filter logic
  const filteredAssets = assets.filter(asset => {
    const matchesSearch = asset.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          asset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (asset.siteName && asset.siteName.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesType = filterType === 'ALL' || asset.type === filterType;
    const matchesStatus = filterStatus === 'ALL' || asset.status === filterStatus;

    return matchesSearch && matchesType && matchesStatus;
  });

  // Calculate high-level summary metrics
  const totalRented = assets.length;
  const totalIdleHours = assets.reduce((acc, a) => acc + (a.idleHours || a.idleHoursPerDay || 0), 0);
  const totalEngineHours = assets.reduce((acc, a) => acc + (a.engineHours || a.engineHoursPerDay || 0), 0);
  const wastedFuelCost = (totalIdleHours * 22.5).toFixed(0); // Estimated $22.50/hr idle burn

  return (
    <div className="space-y-6">
      {/* Top Operations KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#181818] p-4 rounded-xl border border-[#2B2B2B]">
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-1">
            <span>Total Rented Fleet</span>
            <Activity className="w-4 h-4 text-[#FFCD11]" />
          </div>
          <div className="text-2xl font-black text-white">{totalRented} <span className="text-xs font-normal text-neutral-400">Heavy Units</span></div>
          <div className="text-[11px] text-emerald-400 mt-1">● Active on 4 project sites</div>
        </div>

        <div className="bg-[#181818] p-4 rounded-xl border border-[#2B2B2B]">
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-1">
            <span>Total Engine Work</span>
            <Clock className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-emerald-400">{totalEngineHours.toFixed(1)} <span className="text-xs font-normal text-neutral-400">hrs</span></div>
          <div className="text-[11px] text-neutral-400 mt-1">Productive equipment hours</div>
        </div>

        <div className="bg-[#181818] p-4 rounded-xl border border-[#2B2B2B]">
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-1">
            <span>Idle Hours (Underutilized)</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-black text-amber-400">{totalIdleHours.toFixed(1)} <span className="text-xs font-normal text-neutral-400">hrs</span></div>
          <div className="text-[11px] text-amber-300 mt-1">⚠️ High idle ratio on 2 units</div>
        </div>

        <div className="bg-[#181818] p-4 rounded-xl border border-[#2B2B2B]">
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-1">
            <span>Idle Expense Loss</span>
            <DollarSign className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-black text-rose-400">${wastedFuelCost}</div>
          <div className="text-[11px] text-rose-300/80 mt-1">Wasted on idle machinery</div>
        </div>
      </div>

      {/* Control Bar: Search, Filters & Action Buttons */}
      <div className="bg-[#181818] p-4 rounded-xl border border-[#2B2B2B] flex flex-wrap gap-3 items-center justify-between">
        <div className="flex items-center gap-3 flex-1 min-w-[260px]">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-neutral-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by ID (EQX1001), Model, or Site..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-[#FFCD11]"
            />
          </div>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-[#111] border border-[#333] rounded-lg px-3 py-2 text-xs text-neutral-300 focus:outline-none focus:border-[#FFCD11]"
          >
            <option value="ALL">All Types</option>
            <option value="Excavator">Excavators</option>
            <option value="Bulldozer">Bulldozers</option>
            <option value="Crane">Cranes</option>
            <option value="Grader">Graders</option>
          </select>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-[#111] border border-[#333] rounded-lg px-3 py-2 text-xs text-neutral-300 focus:outline-none focus:border-[#FFCD11]"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active (Optimal)</option>
            <option value="IDLE_WARNING">Idle Warning</option>
            <option value="CRITICAL_ALERT">Critical Anomaly</option>
          </select>
        </div>

        {/* Check-In / Check-Out Action Button */}
        <button
          onClick={onOpenCheckInOut}
          className="bg-[#FFCD11] hover:bg-[#E5B80E] text-black font-extrabold px-4 py-2 rounded-lg text-xs transition flex items-center shadow-md cursor-pointer"
        >
          <QrCode className="w-4 h-4 mr-1.5" />
          QR Check-In / Check-Out
        </button>
      </div>

      {/* Rented Equipment Master Table */}
      <div className="bg-[#181818] rounded-xl border border-[#2B2B2B] overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[#2B2B2B] flex items-center justify-between">
          <h3 className="text-sm font-bold text-white flex items-center">
            Rented Machinery Tracking Register
            <span className="ml-2 bg-[#2B2B2B] text-neutral-300 text-[10px] px-2 py-0.5 rounded-full font-semibold">
              {filteredAssets.length} Units
            </span>
          </h3>
          <span className="text-xs text-neutral-400">Live Telemetry Sync: Every 2s</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#141414] text-neutral-400 border-b border-[#2B2B2B] uppercase tracking-wider text-[10px]">
                <th className="py-3 px-4">Equipment ID</th>
                <th className="py-3 px-4">Type & Model</th>
                <th className="py-3 px-4">Assigned Site</th>
                <th className="py-3 px-4">Rental Duration</th>
                <th className="py-3 px-4">Engine vs. Idle</th>
                <th className="py-3 px-4">Operational Status</th>
                <th className="py-3 px-4">Anomaly / Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#242424] text-neutral-200">
              {filteredAssets.map((asset) => {
                const isCritical = asset.status === 'CRITICAL_ALERT';
                const isWarning = asset.status === 'IDLE_WARNING';

                return (
                  <tr 
                    key={asset.id} 
                    className="hover:bg-[#202020] transition cursor-pointer"
                    onClick={() => onSelectAsset(asset)}
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-[#FFCD11]">
                      {asset.id}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-white">{asset.name}</div>
                      <div className="text-[11px] text-neutral-400">{asset.type}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      {asset.siteId ? (
                        <div>
                          <span className="font-bold text-neutral-200">{asset.siteId}</span>
                          <span className="text-[11px] text-neutral-400 block">{asset.siteName}</span>
                        </div>
                      ) : (
                        <span className="text-rose-400 font-bold bg-rose-950/40 px-2 py-0.5 rounded border border-rose-900/50">
                          NULL (Unassigned)
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="text-neutral-300 font-medium">
                        {asset.checkOutDate} → {asset.checkInDate}
                      </div>
                      <span className="text-[10px] text-neutral-500">Auto-return tracked</span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center space-x-2">
                        <span className="text-emerald-400 font-bold">
                          {asset.engineHours || asset.engineHoursPerDay}h run
                        </span>
                        <span className="text-neutral-600">/</span>
                        <span className={`font-bold ${isWarning ? 'text-amber-400' : 'text-neutral-400'}`}>
                          {asset.idleHours || asset.idleHoursPerDay}h idle
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-extrabold tracking-wide ${
                        isCritical ? 'bg-rose-950/70 text-rose-300 border border-rose-600/60' :
                        isWarning ? 'bg-amber-950/70 text-amber-300 border border-amber-600/60' :
                        'bg-emerald-950/70 text-emerald-300 border border-emerald-600/60'
                      }`}>
                        {asset.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {asset.anomaly ? (
                        <span className="text-rose-300 font-medium text-[11px] flex items-center">
                          <AlertTriangle className="w-3.5 h-3.5 text-rose-400 mr-1 shrink-0" />
                          {asset.anomaly}
                        </span>
                      ) : (
                        <span className="text-emerald-400 font-medium text-[11px] flex items-center">
                          <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                          Normal Operation
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}