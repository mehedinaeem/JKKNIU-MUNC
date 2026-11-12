import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import useResource from '../../hooks/useResource';
import { readAttempt, storeAttempt } from '../../services/registration';
import { RegistrationHero } from '../../components/registration/RegistrationUI';
import '../../components/registration/registration.css';

export default function RegistrationConfirmationPage() {
    const { slug, formSlug } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const [receipt] = useState(() => readAttempt(slug, formSlug));
    const [copyMessage, setCopyMessage] = useState('');
    const definition = useResource(`/forms/${encodeURIComponent(formSlug)}/`, false, true);
    const reference = receipt.reference_number || location.state?.reference_number;
    async function copy() {
        try { await navigator.clipboard.writeText(reference); setCopyMessage('Reference copied.'); }
        catch { setCopyMessage('Please select and copy your reference manually.'); }
    }
    return <div className="registration-page registration-confirmation min-h-[70vh] bg-slate-50 pt-24"><RegistrationHero title={reference ? 'Application received' : 'Registration confirmation'}><p>{reference ? 'Thank you for applying to participate with JKKNIU MUNC.' : 'A successful submission is needed to receive a reference number.'}</p></RegistrationHero><main className="mx-auto max-w-3xl px-4 py-12 sm:px-6"><section className="registration-panel text-center">
        {reference ? <><span aria-hidden="true" className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-3xl text-emerald-700">✓</span><h2 className="text-2xl text-primary-900">Your application is safely received</h2><p className="mt-4 text-sm leading-7 text-slate-600">Keep this reference number for any communication with the organisers.</p><p className="mt-7 text-xs font-semibold uppercase tracking-widest text-slate-500">Registration reference</p><p className="mt-3 select-all break-all rounded-xl border border-primary-100 bg-primary-50 p-5 font-mono text-lg font-bold text-primary-800 sm:text-2xl" aria-label="Registration reference number">{reference}</p><div className="registration-no-print mt-5 flex flex-wrap justify-center gap-3"><button type="button" className="btn-primary" onClick={copy}>Copy reference</button><button type="button" className="rounded-lg border border-slate-300 px-5 py-3 text-sm font-semibold text-primary-700" onClick={() => window.print()}>Print confirmation</button></div><p role="status" className="mt-3 text-sm text-primary-700">{copyMessage}</p><p className="mt-7 rounded-xl bg-accent-50 p-4 text-sm leading-7 text-slate-700">This confirms receipt of your application. It does not confirm selection, approval, or payment verification.</p></> : <><h2 className="text-xl text-primary-900">No confirmation is stored in this tab</h2><p className="mt-3 text-sm leading-7 text-slate-500">We cannot generate or look up a reference here. If you submitted but did not receive confirmation, return to the same application to retry safely, or contact the organisers.</p></>}
        <div className="registration-no-print mt-8 flex flex-wrap justify-center gap-4"><Link className="text-sm font-semibold text-primary-700 underline underline-offset-4" to={`/events/${encodeURIComponent(slug)}/register`}>Registration categories</Link><Link className="text-sm font-semibold text-primary-700 underline underline-offset-4" to="/events">Events archive</Link></div>
        {reference && definition.data?.event_slug === slug && definition.data?.accepting_submissions && definition.data?.allow_multiple_submissions && <button type="button" className="registration-no-print mt-6 text-sm font-semibold text-primary-700 underline underline-offset-4" onClick={() => { if (window.confirm('Start a separate application? Your existing application will remain on record.')) { storeAttempt(slug, formSlug, {}); navigate(`/events/${encodeURIComponent(slug)}/register/${encodeURIComponent(formSlug)}`); } }}>Start a separate application</button>}
    </section></main></div>;
}
