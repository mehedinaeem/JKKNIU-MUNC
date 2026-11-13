import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import MembershipApplicationForm from './MembershipApplicationForm';
import { api, memberPhoto } from '../../services/api';
import { Button, Control, ErrorNotice, Loading, Notice } from '../../components/admin/AdminUI';
import '../../components/admin/admin.css';

const titles = { join: 'Your place in the conversation', apply: 'Apply for membership', activate: 'Activate your member account', login: 'Welcome back', forgot: 'Recover your account', reset: 'Set a new password', dashboard: 'Your membership', profile: 'Member profile', settings: 'Account settings' };
const descriptions = { join: 'Develop your voice. Explore diplomacy. Build a community.', apply: 'Check your student details, confirm your identity and complete your membership request.', activate: 'Selected members receive a private invitation from an authorized club officer.', login: 'Sign in with your registration number or verified email address.' };
function readToken() {
    const token = new URLSearchParams(window.location.hash.slice(1)).get('token') || '';
    return token;
}

export default function MemberPortal({ mode = 'join' }) {
    const navigate = useNavigate();
    const [invitationLoaded] = useState(() => Boolean(new URLSearchParams(window.location.hash.slice(1)).get('token')));
    const [form, setForm] = useState(() => ({ token: readToken(), consent: false, contact_preference: 'email' }));
    const [member, setMember] = useState(null);
    const [announcements, setAnnouncements] = useState([]);
    const [events, setEvents] = useState([]);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState('');
    const [photo, setPhoto] = useState('');
    const [revision, setRevision] = useState(0);
    useEffect(() => {
        if (form.token && window.location.hash.includes('token=')) window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }, [form.token]);
    const protectedPage = ['dashboard', 'profile', 'settings'].includes(mode);
    useEffect(() => {
        if (!protectedPage) return;
        let live = true;
        const controller = new AbortController();
        api.get('/membership/me/', { signal: controller.signal }).then(value => {
            if (live) { setMember(value); setForm(current => ({ ...current, biography: value.biography, contact_preference: value.contact_preference })); }
        }).catch(failure => { if (!live || failure.name === 'AbortError') return; if ([401, 403].includes(failure.status)) navigate('/member/login', { replace: true }); else setError(failure); });
        if (mode === 'dashboard') {
            api.get('/membership/announcements/', { signal: controller.signal }).then(value => { if (live) setAnnouncements(value); }).catch(failure => { if (live && failure.name !== 'AbortError') setError(failure); });
            api.publicGet('/events/?ordering=start_date', { signal: controller.signal }).then(value => { if (live) setEvents((value.results || []).filter(event => new Date(event.end_date || event.start_date) >= new Date())); }).catch(() => {});
        }
        return () => { live = false; controller.abort(); };
    }, [mode, protectedPage, navigate, revision]);
    useEffect(() => {
        if (!protectedPage) return;
        let live = true; let objectUrl;
        const controller = new AbortController();
        memberPhoto(undefined, { signal: controller.signal }).then(blob => {
            if (live && blob) { objectUrl = URL.createObjectURL(blob); setPhoto(objectUrl); }
        }).catch(() => {});
        return () => { live = false; controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
    }, [protectedPage, revision]);
    function input(key, label, options = {}) {
        return <Control label={label} value={form[key] || ''} onChange={event => setForm({ ...form, [key]: event.target.value })} error={error?.errors?.[key]} {...options} />;
    }
    async function perform(action) {
        if (busy) return;
        setBusy(true); setError(null); setNotice('');
        try { await action(); } catch (failure) { setError(failure); } finally { setBusy(false); }
    }
    async function submit(event) {
        event.preventDefault();
        await perform(async () => {
            let response;
            if (mode === 'login') {
                await api.memberLogin(form.identifier, form.password);
                navigate('/member/dashboard', { replace: true });
            } else if (mode === 'activate' || mode === 'reset') {
                if (form.password !== form.confirm_password) throw new Error('Passwords must match.');
                response = await api.post(mode === 'activate' ? '/membership/activate/' : '/membership/password-reset/confirm/', { token: form.token, password: form.password });
                setNotice(response.detail); setForm({});
            } else if (mode === 'forgot') {
                response = await api.post('/membership/password-reset/request/', { identifier: form.identifier }); setNotice(response.detail);
            } else if (mode === 'profile') {
                await api.patch('/membership/me/', { biography: form.biography || '', contact_preference: form.contact_preference }); setNotice('Profile saved.');
            }
        });
    }
    const content = mode === 'join' ? <JoinContent /> : mode === 'apply' ? <MembershipApplicationForm /> : protectedPage ? !member ? error ? null : <Loading label="Loading your membership…" /> : <>
        <nav aria-label="Member navigation" className="mb-8 flex flex-wrap gap-3">{[['dashboard', 'Overview'], ['profile', 'Profile'], ['settings', 'Settings']].map(([path, label]) => <Link key={path} to={`/member/${path}`} className="admin-button admin-button-secondary">{label}</Link>)}<Button variant="secondary" disabled={busy} onClick={() => perform(async () => { await api.memberLogout(); navigate('/member/login', { replace: true }); })}>Sign out</Button></nav>
        {mode === 'dashboard' && <><div className="grid gap-6 md:grid-cols-3">{[['Member', member.identity.full_name], ['Role', member.role_name], ['Status', member.status.replaceAll('_', ' ')]].map(([label, value]) => <div className="admin-panel" key={label}><p className="text-sm text-slate-500">{label}</p><p className="mt-2 break-words text-xl font-bold text-primary-900">{value}</p></div>)}</div><section className="admin-panel mt-6"><h2 className="text-xl">Official member announcements</h2>{announcements.length ? announcements.map(item => <article key={item.id} className="mt-5 border-t pt-5"><h3>{item.title}</h3><p className="whitespace-pre-wrap text-slate-600">{item.body}</p></article>) : <p className="mt-3 text-slate-500">No published announcements.</p>}</section><section className="admin-panel mt-6"><h2 className="text-xl">Upcoming MUNC events</h2>{events.length ? events.map(item => <Link key={item.id} to={`/events/${item.slug}`} className="mt-3 block text-primary-700 underline">{item.title}</Link>) : <p className="mt-3 text-slate-500">Visit the <Link to="/events" className="underline">events page</Link> for the latest programme.</p>}</section></>}
        {mode === 'profile' && <div className="grid gap-6 lg:grid-cols-2"><section className="admin-panel"><h2 className="text-xl">Verified identity & membership</h2>{photo && <img src={photo} alt="Your profile" className="my-5 h-32 w-32 rounded-2xl object-cover" />}<dl className="mt-5 space-y-4">{[['Full name', member.identity.full_name], ['Registration number', member.identity.registration_number], ['Student ID', member.identity.student_id || 'Not provided'], ['Department', member.identity.department], ['Session', member.identity.session || 'Not provided'], ['Membership ID', member.membership_id], ['Joined', member.joined_at ? new Date(member.joined_at).toLocaleDateString() : 'Pending'], ...member.verified_contacts.map(contact => [`Verified ${contact.kind}`, contact.value])].map(([label, value]) => <div key={label}><dt className="text-sm text-slate-500">{label}</dt><dd className="break-words font-medium text-primary-900">{value}</dd></div>)}</dl><p className="mt-6 text-sm text-slate-500">University identity is read-only. Contact the club office to request a correction.</p></section><form onSubmit={submit} className="admin-panel space-y-5">{input('biography', 'Biography', { as: 'textarea', rows: 5, maxLength: 3000 })}{input('contact_preference', 'Contact preference', { as: 'select', children: <><option value="email">Email</option><option value="phone">Phone, if verified</option><option value="none">No optional contact</option></> })}<Button type="submit" disabled={busy}>Save profile</Button><Control label="Profile photo (PNG or JPEG, up to 2 MiB)" type="file" accept="image/png,image/jpeg" disabled={busy} onChange={event => { const file = event.target.files[0]; if (file) perform(async () => { await api.uploadMemberPhoto(file); setRevision(value => value+1); setNotice('Photo updated.'); }); }} /></form></div>}
        {mode === 'settings' && <div className="grid gap-6 lg:grid-cols-2"><form className="admin-panel space-y-5" onSubmit={event => { event.preventDefault(); perform(async () => { const result = await api.post('/membership/change-password/', { old_password: form.old_password, password: form.password }); setNotice(result.detail); setForm(current => ({ ...current, password: '', old_password: '' })); }); }}><h2 className="text-xl">Change password</h2>{input('old_password', 'Current password', { type: 'password', required: true, autoComplete: 'current-password' })}{input('password', 'New password', { type: 'password', required: true, minLength: 8, maxLength: 128, autoComplete: 'new-password' })}<Button type="submit" disabled={busy}>Update password</Button></form><form className="admin-panel space-y-5" onSubmit={event => { event.preventDefault(); perform(async () => { const data = form.token ? { token: form.token } : { email: form.email, password: form.email_password }; const result = await api.post('/membership/change-email/', data); setNotice(result.detail); setForm(current => ({ ...current, token: '', email_password: '' })); setRevision(value => value+1); }); }}><h2 className="text-xl">Verified email</h2><p className="text-sm text-slate-500">A new address becomes your login contact only after you confirm its private verification link.</p>{form.token ? <p>Private verification link loaded. Confirm to update your email.</p> : <>{input('email', 'New email', { type: 'email', required: true, maxLength: 254 })}{input('email_password', 'Confirm current password', { type: 'password', required: true, autoComplete: 'current-password' })}</>}<Button type="submit" disabled={busy}>{form.token ? 'Confirm email change' : 'Send verification link'}</Button></form></div>}
    </> : <div className="mx-auto max-w-xl"><form onSubmit={submit} className="admin-panel space-y-5">
        {(mode === 'login' || mode === 'forgot') && input('identifier', 'Registration number or verified email', { required: true, maxLength: 254, autoComplete: 'username' })}
        {mode === 'login' && input('password', 'Password', { type: 'password', required: true, maxLength: 128, autoComplete: 'current-password' })}
        {(mode === 'activate' || mode === 'reset') && <>{!invitationLoaded ? <p className="rounded-xl bg-primary-50 p-4 text-sm">Open the private link supplied by the club {mode === 'activate' ? 'officer' : 'recovery email'}, or paste its invitation token below. Your registration number cannot activate an account.</p> : <p className="text-sm text-slate-600">Private invitation loaded. Choose a strong, unique password.</p>}{!invitationLoaded && input('token', 'Private invitation token', { type: 'password', required: true, minLength: 40, maxLength: 128, autoComplete: 'off' })}{input('password', 'New password', { type: 'password', required: true, minLength: 8, maxLength: 128, autoComplete: 'new-password' })}{input('confirm_password', 'Confirm new password', { type: 'password', required: true, minLength: 8, maxLength: 128, autoComplete: 'new-password' })}</>}
        <Button type="submit" disabled={busy} className="w-full">{busy ? 'Please wait…' : { apply: 'Submit application', activate: 'Activate account', login: 'Sign in', forgot: 'Request recovery instructions', reset: 'Reset password' }[mode]}</Button><div className="flex flex-wrap justify-between gap-4 text-sm"><Link to="/join" className="text-primary-700 underline">Membership portal</Link>{mode === 'login' ? <Link to="/member/forgot-password" className="text-primary-700 underline">Forgot password?</Link> : <Link to="/member/login" className="text-primary-700 underline">Member login</Link>}</div></form></div>;
    return <div className="admin-app min-h-screen bg-slate-50 pb-20 pt-28"><div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8"><header className="py-10 md:py-14"><p className="text-xs font-bold uppercase tracking-[.2em] text-primary-600">JKKNIU MUNC · Membership</p><h1 className="mt-4 max-w-4xl font-heading text-4xl font-bold text-primary-900 md:text-5xl">{titles[mode]}</h1>{descriptions[mode] && <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">{descriptions[mode]}</p>}</header><ErrorNotice error={error} /><Notice>{notice}</Notice>{content}<p className="mt-10 text-center text-sm text-slate-500">Need help? <Link to="/contact" className="font-semibold text-primary-700 underline">Contact the MUNC office</Link></p></div></div>;
}

function JoinContent() {
    return <><section className="grid gap-5 md:grid-cols-3" aria-label="Choose your membership journey">{[['01', 'Apply for Membership', 'For students who want to join our community of diplomacy, debate and leadership.', '/join/apply', 'Start an application'], ['02', 'Activate Member Account', 'Already selected? Use the private invitation issued after identity confirmation.', '/join/activate', 'Activate your account'], ['03', 'Member Login', 'Access your profile, membership details and official club announcements.', '/member/login', 'Sign in']].map(([number, title, description, to, action]) => <article className="admin-panel flex flex-col" key={number}><span className="text-sm font-bold text-primary-500">{number}</span><h2 className="mt-5 text-2xl">{title}</h2><p className="mb-7 mt-3 flex-1 leading-7 text-slate-600">{description}</p><Link to={to} className="admin-button admin-button-primary">{action} →</Link></article>)}</section><div className="mt-12 grid gap-8 lg:grid-cols-2"><section className="admin-panel"><h2 className="text-2xl">Learn together. Lead with purpose.</h2><p className="mt-4 leading-7 text-slate-600">JKKNIU Model United Nations Club brings students together to explore international affairs, practise negotiation and develop confidence in public speaking.</p><ul className="mt-5 list-disc space-y-3 pl-5 text-slate-600"><li>Build research, communication and negotiation skills.</li><li>Meet students with an interest in global issues.</li><li>Explore opportunities to contribute to club programmes.</li></ul></section><section className="admin-panel"><h2 className="text-2xl">How membership works</h2><ol className="mt-5 list-decimal space-y-4 pl-5 text-slate-600"><li>Check your registration number, confirm your student details and provide your email. New applicants also explain why they would like to join.</li><li>The club reviews eligibility and confirms identity ownership independently.</li><li>Selected students receive a private, time-limited invitation.</li><li>Set your password and access your member account.</li></ol><p className="mt-5 text-sm text-slate-500">You need an eligible JKKNIU student record. Application submission does not guarantee selection or confer account access.</p></section></div><section className="admin-panel mt-8"><h2 className="text-2xl">Questions before you join</h2>{[['Do I need previous MUN experience?', 'Describe your experience honestly, including if you are new to MUN. The club reviews each application.'], ['Can I activate using my registration number?', 'No. Activation requires a private invitation issued after independent identity confirmation.'], ['I do not have a verified email. What can I do?', 'Contact the club office to arrange in-person identity confirmation and private invitation delivery.'], ['My university record could not be checked.', 'Contact the club office. Verification depends on an authorized university integration; never share your bank password or payment credentials.']].map(([question, answer]) => <details key={question} className="border-b border-slate-100 py-5"><summary className="cursor-pointer font-semibold text-primary-900">{question}</summary><p className="mt-3 max-w-3xl leading-7 text-slate-600">{answer}</p></details>)}</section></>;
}
