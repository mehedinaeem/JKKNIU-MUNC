import { useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import useAdminAuth from '../../hooks/useAdminAuth';
import { Button, ErrorNotice } from './AdminUI';

export default function AdminLayout() {
    const auth = useAdminAuth();
    const [menuOpen, setMenuOpen] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    async function signOut() {
        if (auth.navigationGuardRef.current && !auth.navigationGuardRef.current()) return;
        setBusy(true);
        try { await auth.logout(); } catch (failure) { setError(failure); } finally { setBusy(false); }
    }
    const links = [['/admin', 'Overview', '◈'], ['/admin/events', 'Events', '▦'], ['/admin/submissions', 'Applications', '▧'], ...(auth.canManage ? [['/admin/forms', 'Registration forms', '▤']] : [])];
    return <div className="admin-app admin-shell lg:flex">
        <a className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:p-3" href="#admin-main">Skip to main content</a>
        <aside className="bg-primary-900 text-white lg:fixed lg:inset-y-0 lg:w-64 lg:flex lg:flex-col">
            <div className="flex items-center justify-between p-5 lg:px-6 lg:py-8"><Link to="/admin" className="admin-nav flex min-w-0 items-center gap-3 rounded-lg"><img src="/mun-logo.png" alt="" className="h-11 w-11 object-contain" /><span><span className="block font-heading text-sm font-bold tracking-wide">JKKNIU MUNC</span><span className="mt-1 block text-[10px] font-semibold uppercase tracking-[.2em] text-accent-300">Administration</span></span></Link><button type="button" className="admin-nav rounded-lg border border-white/20 px-3 py-2 text-sm lg:hidden" aria-expanded={menuOpen} aria-controls="admin-navigation" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? 'Close' : 'Menu'}</button></div>
            <nav id="admin-navigation" aria-label="Administration" className={`${menuOpen ? 'block' : 'hidden'} space-y-2 px-4 pb-5 lg:block lg:flex-1 lg:pt-3`}>
                {links.map(([to, label, icon]) => <NavLink key={to} to={to} end={to === '/admin'} onClick={() => setMenuOpen(false)} className={({ isActive }) => `admin-nav flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium ${isActive ? 'bg-white/10 text-accent-300 ring-1 ring-white/10' : 'text-slate-300 hover:bg-white/5 hover:text-white'}`}><span aria-hidden="true" className="text-lg">{icon}</span>{label}</NavLink>)}
                <Link to="/" className="admin-nav mt-8 flex items-center gap-3 rounded-xl px-4 py-3 text-sm text-slate-400 hover:text-white"><span aria-hidden="true">↗</span> Visit public website</Link>
            </nav>
            <div className="hidden border-t border-white/10 p-6 lg:block"><p className="text-xs font-medium text-slate-300">Diplomacy. Leadership. Impact.</p><p className="mt-2 text-xs text-slate-500">Your workspace for club registrations.</p></div>
        </aside>
        <div className="min-w-0 flex-1 lg:ml-64">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-4 sm:px-8"><div className="min-w-0 max-w-full"><p className="break-all text-sm font-semibold text-primary-900">{auth.administrator.username}</p><p className="mt-1 text-xs text-slate-500">{auth.administrator.roles.join(' · ')}</p></div><Button variant="secondary" disabled={busy} onClick={signOut}>{busy ? 'Signing out…' : 'Sign out'}</Button></div>
            <main id="admin-main" className="mx-auto w-full max-w-[1440px] p-4 py-7 sm:p-8 lg:p-10"><ErrorNotice error={error} /><Outlet /></main>
        </div>
    </div>;
}
