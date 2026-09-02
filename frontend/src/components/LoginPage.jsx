import React, { useState } from 'react';
import { Building2, LockKeyhole, ShieldCheck, Wrench } from 'lucide-react';
import CatLogo from './CatLogo';
import { useAuth } from '../auth/useAuth';

export default function LoginPage() {
  const { login } = useAuth();
  const [portal, setPortal] = useState('customer');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try { await login(email.trim(), password, portal); }
    catch (err) { setError(err.message || 'Sign in failed.'); }
    finally { setSubmitting(false); }
  };

  return (
    <main className="min-h-dvh bg-[#0b0b0b] text-white grid lg:grid-cols-[1.1fr_0.9fr]">
      <section className="hidden lg:flex relative overflow-hidden border-r border-[#282828] p-12 flex-col justify-between bg-[radial-gradient(circle_at_30%_20%,rgba(255,205,17,.18),transparent_35%),linear-gradient(145deg,#181818,#090909)]">
        <CatLogo className="h-12 w-fit" />
        <div className="max-w-xl">
          <p className="text-[#FFCD11] text-xs font-black uppercase tracking-[0.25em] mb-4">Smart rental operations</p>
          <h1 className="text-5xl font-black leading-tight">Every asset.<br />Every hour.<br /><span className="text-[#FFCD11]">Fully accountable.</span></h1>
          <p className="mt-6 text-neutral-400 max-w-md">Live fleet telemetry, utilization intelligence, predictive maintenance and safety control in one secure workspace.</p>
        </div>
        <p className="text-xs text-neutral-600">CATstats Operations Platform</p>
      </section>

      <section className="flex items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-md">
          <CatLogo className="lg:hidden h-10 w-fit mb-10" />
          <h2 className="text-2xl font-black">Sign in to CATstats</h2>
          <p className="text-sm text-neutral-400 mt-1 mb-7">Choose the workspace assigned to your account.</p>

          <div className="grid grid-cols-2 gap-3 mb-6" role="radiogroup" aria-label="Account type">
            {[
              ['customer', Building2, 'Customer', 'Apex fleet dashboard'],
              ['cat_admin', Wrench, 'Caterpillar Admin', 'Manage asset catalog'],
            ].map(([value, Icon, title, subtitle]) => (
              <button key={value} type="button" role="radio" aria-checked={portal === value} onClick={() => setPortal(value)} className={`text-left rounded-xl border p-3 transition cursor-pointer ${portal === value ? 'border-[#FFCD11] bg-[#FFCD11]/10' : 'border-[#303030] bg-[#151515] hover:border-neutral-500'}`}>
                <Icon className={`w-5 h-5 mb-2 ${portal === value ? 'text-[#FFCD11]' : 'text-neutral-400'}`} />
                <span className="block text-xs font-bold">{title}</span>
                <span className="block text-[10px] text-neutral-500 mt-0.5">{subtitle}</span>
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div><label htmlFor="email" className="block text-xs font-bold text-neutral-300 mb-1.5">Work email</label><input id="email" type="text" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-xl border border-[#333] bg-[#141414] px-4 py-3 text-sm outline-none focus:border-[#FFCD11]" placeholder="Any value for demo access" /></div>
            <div><label htmlFor="password" className="block text-xs font-bold text-neutral-300 mb-1.5">Password</label><input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-xl border border-[#333] bg-[#141414] px-4 py-3 text-sm outline-none focus:border-[#FFCD11]" placeholder="Any value for demo access" /></div>
            {error && <p role="alert" className="rounded-lg border border-rose-900 bg-rose-950/40 px-3 py-2 text-xs text-rose-300">{error}</p>}
            <button disabled={submitting} className="w-full rounded-xl bg-[#FFCD11] py-3 text-sm font-black text-black hover:bg-[#e7ba0e] disabled:opacity-60 cursor-pointer flex items-center justify-center gap-2"><LockKeyhole className="w-4 h-4" />{submitting ? 'Signing in…' : `Open ${portal === 'cat_admin' ? 'Admin' : 'Customer'} workspace`}</button>
          </form>
          <p className="flex items-center justify-center gap-1.5 mt-6 text-[11px] text-amber-500"><ShieldCheck className="w-3.5 h-3.5" />Temporary demo access — authentication disabled</p>
        </div>
      </section>
    </main>
  );
}
