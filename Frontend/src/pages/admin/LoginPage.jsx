import { useState } from 'react';
import { Link, Navigate, useLocation } from 'react-router-dom';
import useAdminAuth from '../../hooks/useAdminAuth';
import { Button, Control, ErrorNotice, Loading } from '../../components/admin/AdminUI';

export default function LoginPage() {
    const auth = useAdminAuth();
    const location = useLocation();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    const requested = location.state?.from;
    const destination = typeof requested === 'string' && /^\/admin(?:\/|$)/.test(requested) && !requested.startsWith('/admin/login') ? requested : '/admin';
    if (auth.checking) return <div className="admin-app admin-shell"><Loading label="Checking your session…" /></div>;
    if (auth.administrator) return <Navigate to={destination} replace />;
    async function submit(event) {
        event.preventDefault();
        setBusy(true); setError(null);
        try { await auth.login(username, password); setPassword(''); } catch (failure) { setError(failure); setPassword(''); } finally { setBusy(false); }
    }
    return <div className="admin-app grid min-h-screen bg-slate-50 lg:grid-cols-2">
        <div className="relative hidden flex-col justify-between overflow-hidden bg-primary-900 p-12 text-white lg:flex"><div className="absolute -right-24 top-24 h-96 w-96 rounded-full border border-white/10" aria-hidden="true" /><div className="absolute -right-12 top-36 h-72 w-72 rounded-full border border-accent-400/20" aria-hidden="true" /><Link to="/" className="relative flex items-center gap-3"><img src="/mun-logo.png" className="h-16 w-16 object-contain" alt="JKKNIU MUNC" /><span className="font-heading text-lg font-bold">JKKNIU MUNC</span></Link><div className="relative max-w-lg"><p className="mb-5 text-xs font-semibold uppercase tracking-[.2em] text-accent-300">Built for the people behind the events</p><h1 className="text-4xl font-bold leading-tight xl:text-5xl">Great experiences<br />start with a<br /><span className="text-accent-400">thoughtful welcome.</span></h1><p className="mt-6 max-w-sm leading-7 text-slate-300">Create registration forms, organize your events and make every application count.</p></div><p className="text-xs text-slate-400">Jatiya Kabi Kazi Nazrul Islam University</p></div>
        <main className="flex items-center justify-center p-5 py-12 sm:p-12"><div className="w-full max-w-md"><Link to="/" className="mb-8 inline-block text-sm font-medium text-primary-600">← Back to the website</Link><p className="text-xs font-bold uppercase tracking-[.18em] text-primary-600">Administrator access</p><h2 className="mt-3 text-3xl font-bold text-primary-900">Welcome back</h2><p className="mb-8 mt-3 text-sm leading-6 text-slate-500">Sign in with your club administration account.</p>
            <ErrorNotice error={error || auth.error} />
            <form onSubmit={submit} className="space-y-5"><Control label="Username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required maxLength={150} disabled={busy} /><Control label="Password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required maxLength={1024} disabled={busy} /><Button type="submit" className="w-full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in to your workspace'}<span aria-hidden="true">→</span></Button></form><p className="mt-6 text-xs leading-6 text-slate-500">Access is assigned by a Super Admin. Contact your club administrator if you need an account or a different event assignment.</p>
        </div></main>
    </div>;
}
