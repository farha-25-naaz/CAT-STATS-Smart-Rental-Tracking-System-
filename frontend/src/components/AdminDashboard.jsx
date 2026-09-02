import React, { useCallback, useEffect, useState } from 'react';
import { LogOut, Pencil, RefreshCw, Save, Search, ShieldCheck, X } from 'lucide-react';
import CatLogo from './CatLogo';
import { useAuth } from '../auth/useAuth';
import { assetAdminApi } from '../auth/supabase';

const EDITABLE_FIELDS = ['type', 'status', 'current_site_id', 'current_operator_id', 'rental_rate_per_day', 'idle_cost_per_hour'];

export default function AdminDashboard() {
  const { session, profile, logout } = useAuth();
  const [assets, setAssets] = useState([]);
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState(null);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setStatus('loading'); setError('');
    try { setAssets(await assetAdminApi.list(session.access_token)); setStatus('ready'); }
    catch (err) { setError(err.message); setStatus('error'); }
  }, [session.access_token]);

  useEffect(() => {
    // Synchronize the admin table with the authenticated Supabase data source.
    // eslint-disable-next-line react/set-state-in-effect
    load();
  }, [load]);

  const save = async (event) => {
    event.preventDefault();
    setStatus('saving'); setError('');
    const values = Object.fromEntries(EDITABLE_FIELDS.map((key) => [key, editing[key] === '' ? null : editing[key]]));
    for (const key of ['rental_rate_per_day', 'idle_cost_per_hour']) {
      if (values[key] != null) values[key] = Number(values[key]);
    }
    try {
      const [updated] = await assetAdminApi.update(session.access_token, editing.asset_id, values);
      setAssets((items) => items.map((item) => item.asset_id === updated.asset_id ? updated : item));
      setEditing(null); setStatus('ready');
    } catch (err) { setError(err.message); setStatus('error'); }
  };

  const visible = assets.filter((asset) => `${asset.asset_id} ${asset.type} ${asset.current_site_id || ''}`.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="min-h-dvh bg-[#0c0c0c] text-neutral-200">
      <header className="sticky top-0 z-20 border-b border-[#282828] bg-[#121212]/95 backdrop-blur px-4 sm:px-7 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4"><CatLogo className="h-8" /><div className="border-l border-[#333] pl-4"><p className="text-xs font-black text-white">Caterpillar Administration</p><p className="text-[10px] text-[#FFCD11] flex items-center gap-1"><ShieldCheck className="w-3 h-3" />Authorized asset management</p></div></div>
        <div className="flex items-center gap-3"><div className="text-right hidden sm:block"><p className="text-xs font-bold text-white">{profile.full_name || profile.email}</p><p className="text-[10px] text-neutral-500">Caterpillar administrator</p></div><button onClick={logout} className="rounded-lg border border-[#333] bg-[#1b1b1b] px-3 py-2 text-xs font-bold hover:bg-[#252525] cursor-pointer flex items-center gap-1.5"><LogOut className="w-3.5 h-3.5" />Sign out</button></div>
      </header>

      <main className="p-4 sm:p-7 max-w-[1500px] mx-auto space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4"><div><p className="text-[10px] uppercase tracking-[.2em] text-[#FFCD11] font-black">Asset catalog</p><h1 className="text-2xl font-black text-white mt-1">Fleet Administration</h1><p className="text-xs text-neutral-500 mt-1">Review and update Caterpillar rental equipment records.</p></div><button onClick={load} disabled={status === 'loading'} className="self-start rounded-lg border border-[#333] px-3 py-2 text-xs font-bold hover:bg-[#202020] disabled:opacity-50 cursor-pointer flex items-center gap-1.5"><RefreshCw className={`w-3.5 h-3.5 ${status === 'loading' ? 'animate-spin' : ''}`} />Refresh</button></div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">{[['Total assets', assets.length], ['Active', assets.filter(a => a.status === 'ACTIVE').length], ['Unassigned', assets.filter(a => a.status === 'UNASSIGNED').length], ['Safety lockouts', assets.filter(a => a.status === 'SAFETY_LOCKOUT').length]].map(([label, value]) => <div key={label} className="rounded-xl border border-[#292929] bg-[#171717] p-4"><p className="text-[11px] text-neutral-500">{label}</p><p className="text-2xl font-black text-white mt-1">{value}</p></div>)}</div>
        <div className="rounded-xl border border-[#292929] bg-[#171717] overflow-hidden">
          <div className="p-4 border-b border-[#292929]"><div className="relative max-w-md"><Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search asset ID, type or site" className="w-full rounded-lg border border-[#333] bg-[#101010] pl-9 pr-3 py-2 text-xs outline-none focus:border-[#FFCD11]" /></div></div>
          {error && <div role="alert" className="m-4 rounded-lg border border-rose-900 bg-rose-950/40 p-3 text-xs text-rose-300">{error}</div>}
          <div className="overflow-x-auto"><table className="w-full text-xs"><thead className="bg-[#101010] text-neutral-500 uppercase text-[10px]"><tr>{['Asset ID', 'Type', 'Status', 'Site', 'Operator', 'Daily rate', 'Action'].map(h => <th key={h} className="text-left px-4 py-3 whitespace-nowrap">{h}</th>)}</tr></thead><tbody className="divide-y divide-[#292929]">{visible.map(asset => <tr key={asset.asset_id} className="hover:bg-[#1c1c1c]"><td className="px-4 py-3 font-mono font-black text-[#FFCD11]">{asset.asset_id}</td><td className="px-4 py-3">{asset.type || '—'}</td><td className="px-4 py-3"><span className="rounded bg-[#262626] px-2 py-1 text-[10px] font-bold">{asset.status}</span></td><td className="px-4 py-3">{asset.current_site_id || '—'}</td><td className="px-4 py-3">{asset.current_operator_id || '—'}</td><td className="px-4 py-3">{asset.rental_rate_per_day ?? '—'}</td><td className="px-4 py-3"><button onClick={() => setEditing({ ...asset })} className="rounded-lg bg-[#FFCD11] px-2.5 py-1.5 font-black text-black cursor-pointer flex items-center gap-1"><Pencil className="w-3 h-3" />Edit</button></td></tr>)}</tbody></table></div>
          {status === 'loading' && <p className="p-8 text-center text-xs text-neutral-500">Loading assets…</p>}
          {status !== 'loading' && !visible.length && <p className="p-8 text-center text-xs text-neutral-500">No matching assets.</p>}
        </div>
      </main>

      {editing && <div className="fixed inset-0 z-50 overflow-y-auto bg-black/80 p-3 flex items-start sm:items-center justify-center"><form onSubmit={save} className="w-full max-w-lg max-h-[calc(100dvh-1.5rem)] overflow-y-auto rounded-2xl border border-[#353535] bg-[#171717] p-5 shadow-2xl"><div className="flex justify-between items-start mb-5"><div><p className="text-[10px] text-[#FFCD11] uppercase font-black tracking-widest">Edit asset</p><h2 className="text-lg font-black text-white mt-1">{editing.asset_id}</h2></div><button type="button" aria-label="Close" onClick={() => setEditing(null)} className="p-2 rounded-lg hover:bg-[#252525] cursor-pointer"><X className="w-4 h-4" /></button></div><div className="grid sm:grid-cols-2 gap-4">
        <Field label="Equipment type" value={editing.type} onChange={v => setEditing(e => ({ ...e, type: v }))} />
        <label className="text-xs font-bold text-neutral-300">Status<select value={editing.status || ''} onChange={e => setEditing(a => ({ ...a, status: e.target.value }))} className="mt-1.5 w-full rounded-lg border border-[#333] bg-[#101010] px-3 py-2.5 text-white"><option>ACTIVE</option><option>IDLE</option><option>OVERDUE</option><option>UNASSIGNED</option><option>SAFETY_LOCKOUT</option></select></label>
        <Field label="Site ID" value={editing.current_site_id} onChange={v => setEditing(e => ({ ...e, current_site_id: v }))} />
        <Field label="Operator ID" value={editing.current_operator_id} onChange={v => setEditing(e => ({ ...e, current_operator_id: v }))} />
        <Field label="Daily rental rate" type="number" value={editing.rental_rate_per_day} onChange={v => setEditing(e => ({ ...e, rental_rate_per_day: v }))} />
        <Field label="Idle cost per hour" type="number" value={editing.idle_cost_per_hour} onChange={v => setEditing(e => ({ ...e, idle_cost_per_hour: v }))} />
      </div><button disabled={status === 'saving'} className="mt-6 w-full rounded-xl bg-[#FFCD11] py-3 text-sm font-black text-black disabled:opacity-50 cursor-pointer flex justify-center items-center gap-2"><Save className="w-4 h-4" />{status === 'saving' ? 'Saving…' : 'Save changes'}</button></form></div>}
    </div>
  );
}

function Field({ label, value, onChange, type = 'text' }) {
  return <label className="text-xs font-bold text-neutral-300">{label}<input type={type} step={type === 'number' ? '0.01' : undefined} value={value ?? ''} onChange={e => onChange(e.target.value)} className="mt-1.5 w-full rounded-lg border border-[#333] bg-[#101010] px-3 py-2.5 text-white outline-none focus:border-[#FFCD11]" /></label>;
}
