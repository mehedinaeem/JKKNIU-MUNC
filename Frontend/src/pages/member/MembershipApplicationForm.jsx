import { useId, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import { Button, Control, ErrorNotice, Notice } from '../../components/admin/AdminUI';

export default function MembershipApplicationForm() {
    const membershipErrorId = useId();
    const [number, setNumber] = useState('');
    const [consent, setConsent] = useState(false);
    const [lookup, setLookup] = useState(null);
    const [confirmed, setConfirmed] = useState(false);
    const [existing, setExisting] = useState('');
    const [email, setEmail] = useState('');
    const [motivation, setMotivation] = useState('');
    const [experience, setExperience] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState('');
    function resetRecord() { setLookup(null); setConfirmed(false); setExisting(''); setMotivation(''); setExperience(''); setError(null); }
    async function submit(event) {
        event.preventDefault();
        if (busy) return;
        setBusy(true); setError(null); setNotice('');
        try {
            if (!lookup) {
                const checked = await api.post('/membership/lookup/', { registration_number: number.trim(), consent });
                setLookup(checked); setConfirmed(false);
            } else {
                const result = await api.post('/membership/apply/', {
                    registration_number: lookup.student.registration_number, lookup_token: lookup.lookup_token,
                    identity_confirmed: confirmed, is_existing_member: existing === 'yes', contact_email: email,
                    motivation: existing === 'no' ? motivation : '', experience: existing === 'no' ? experience : '',
                    contact_preference: 'email', consent,
                });
                setNotice(`${result.detail} Reference: ${result.reference}`);
                setLookup(null); setNumber(''); setConfirmed(false); setExisting(''); setEmail(''); setMotivation(''); setExperience(''); setConsent(false);
            }
        } catch (failure) { setError(failure); } finally { setBusy(false); }
    }
    return <div className="mx-auto max-w-2xl"><ErrorNotice error={error} /><Notice>{notice}</Notice><form onSubmit={submit} className="admin-panel space-y-6">
        <div><p className="text-xs font-bold uppercase tracking-widest text-primary-600">Step {lookup ? '2 of 2 · Confirm & submit' : '1 of 2 · Find your student record'}</p><h2 className="mt-3 text-2xl text-primary-900">{lookup ? 'Is this you?' : 'Check your university registration'}</h2><p className="mt-3 text-sm leading-6 text-slate-600">{lookup ? 'Check the student details below. If they are yours, confirm and complete your application.' : 'Enter your own registration number to retrieve your student details from the university fee lookup.'}</p></div>
        <Control label="University registration number" value={number} required maxLength={64} readOnly={!!lookup} disabled={busy} onChange={event => setNumber(event.target.value)} error={error?.errors?.registration_number} />
        {lookup && <><section aria-label="Your student record" className="rounded-2xl border border-primary-100 bg-primary-50 p-5"><p className="text-lg font-bold text-primary-900">{lookup.student.full_name}</p><dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">{[['Registration number', lookup.student.registration_number], ['Department', lookup.student.department], ['Student ID (partially hidden)', lookup.student.student_id || 'Not supplied']].map(([label, value]) => <div key={label}><dt className="text-slate-500">{label}</dt><dd className="mt-1 break-words font-semibold text-primary-900">{value}</dd></div>)}</dl><Button variant="secondary" className="mt-5" disabled={busy} onClick={resetRecord}>No, change registration number</Button></section>
        <label className="flex items-start gap-3 rounded-xl border p-4 text-sm font-semibold"><input type="checkbox" required checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} className="mt-1" />Yes, this is me. These are my student details.</label>
        <fieldset disabled={busy} aria-describedby={error?.errors?.is_existing_member ? membershipErrorId : undefined}>
            <legend className="admin-label">Are you already a MUNC member? <span aria-hidden="true" className="text-red-600">*</span></legend>
            <div className="grid gap-3 sm:grid-cols-2">{[['yes', 'Yes, I am already a member'], ['no', 'No, I would like to join']].map(([value, label]) => <label key={value} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 text-sm font-semibold transition ${existing === value ? 'border-primary-500 bg-primary-50 text-primary-900' : 'border-slate-300 bg-white text-slate-700'}`}><input type="radio" name="existing_membership" value={value} required checked={existing === value} onChange={() => { setExisting(value); if (value === 'yes') { setMotivation(''); setExperience(''); } }} className="mt-0.5" /><span>{label}</span></label>)}</div>
            {error?.errors?.is_existing_member && <p id={membershipErrorId} className="admin-field-error">{error.errors.is_existing_member}</p>}
        </fieldset>
        <Control label="Email address" type="email" required maxLength={254} autoComplete="email" value={email} disabled={busy} onChange={event => setEmail(event.target.value)} error={error?.errors?.contact_email} hint="We will use this for application updates. It is not automatically verified for account activation." />
        {existing === 'no' && <Control label="Why would you like to join MUNC?" as="textarea" required rows={5} minLength={20} maxLength={5000} value={motivation} disabled={busy} onChange={event => setMotivation(event.target.value)} error={error?.errors?.motivation} />}
        {existing === 'no' && <Control label="Relevant experience (optional)" as="textarea" rows={3} maxLength={5000} value={experience} disabled={busy} onChange={event => setExperience(event.target.value)} />}
        <p className="text-xs leading-5 text-slate-500">Your answer about existing membership is self-reported. The club will review your record; confirming these details does not activate an account.</p></>}
        <label className="flex items-start gap-3 text-sm"><input type="checkbox" required checked={consent} disabled={busy} onChange={event => setConsent(event.target.checked)} className="mt-1" />I consent to checking my student record and processing my membership application.</label>
        <Button type="submit" disabled={busy || (!!lookup && (!confirmed || !existing))} className="w-full">{busy ? 'Please wait…' : lookup ? 'Submit application' : 'Show my student details'}</Button>
        {error?.errors?.lookup_token && <p className="text-sm text-red-700">{error.errors.lookup_token} <button type="button" className="underline" onClick={resetRecord}>Check your record again</button></p>}
        <div className="flex flex-wrap justify-between gap-3 text-sm"><Link to="/join" className="text-primary-700 underline">Membership portal</Link><Link to="/member/login" className="text-primary-700 underline">Already activated? Member login</Link></div>
    </form></div>;
}
