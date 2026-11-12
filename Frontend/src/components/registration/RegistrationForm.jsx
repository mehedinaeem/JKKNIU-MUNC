import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useUnsavedChanges from '../../hooks/useUnsavedChanges';
import { readAttempt, storeAttempt, submitRegistration } from '../../services/registration';
import DynamicQuestion from './DynamicQuestion';
import { answerError, initialAnswers, prepareAnswers, SUPPORTED_TYPES, validateRegistration } from './validation';

export default function RegistrationForm({ definition, eventSlug, onReload }) {
    const navigate = useNavigate();
    const fields = definition.schema.fields;
    const [answers, setAnswers] = useState(() => initialAnswers(fields));
    const [files, setFiles] = useState({});
    const [email, setEmail] = useState('');
    const [errors, setErrors] = useState({});
    const [busy, setBusy] = useState(false);
    const [uncertain, setUncertain] = useState(false);
    const [message, setMessage] = useState('');
    const [progress, setProgress] = useState(null);
    const [dirty, setDirty] = useState(false);
    const [recovered] = useState(() => readAttempt(eventSlug, definition.slug));
    const keyRef = useRef(recovered.submission_key || null);
    const inFlightRef = useRef(false);
    const payloadRef = useRef(null);
    const errorRef = useRef(null);
    const contact = fields.find(field => field.field_type === 'email' && field.required);
    const unsupported = fields.some(field => !SUPPORTED_TYPES.includes(field.field_type));
    useUnsavedChanges(dirty || busy || uncertain);
    function focusErrors(next) {
        setErrors(next);
        window.requestAnimationFrame(() => errorRef.current?.focus());
    }
    function edit(key, value) {
        setAnswers(previous => ({ ...previous, [key]: value })); setDirty(true);
        setErrors(previous => ({ ...previous, [key]: '', ...(key === contact?.key ? { applicant_email: '' } : {}) }));
    }
    async function send(event) {
        event.preventDefault();
        if (inFlightRef.current) return;
        if (!uncertain) {
            const applicantEmail = (contact ? answers[contact.key] || '' : email).trim();
            const next = validateRegistration(fields, answers, files, applicantEmail);
            if (contact && next.applicant_email) { next[contact.key] = next.applicant_email; delete next.applicant_email; }
            if (Object.keys(next).length) { focusErrors(next); return; }
            if (!keyRef.current) keyRef.current = crypto.randomUUID();
            storeAttempt(eventSlug, definition.slug, { submission_key: keyRef.current, version: definition.version });
            payloadRef.current = { data: { version: definition.version, applicant_email: applicantEmail,
                answers: prepareAnswers(fields, answers), submission_key: keyRef.current }, files: { ...files } };
        }
        inFlightRef.current = true; setBusy(true); setMessage(''); setErrors({}); setProgress(null);
        try {
            const result = await submitRegistration(definition.slug, payloadRef.current.data, payloadRef.current.files,
                value => setProgress(previous => value == null || previous == null || value === 100 || value >= previous + 5 ? value : previous));
            storeAttempt(eventSlug, definition.slug, { reference_number: result.reference_number, version: definition.version });
            setDirty(false); setUncertain(false);
            navigate(`/events/${encodeURIComponent(eventSlug)}/register/${encodeURIComponent(definition.slug)}/confirmation`,
                { replace: true, state: { reference_number: result.reference_number } });
        } catch (error) {
            const ambiguous = error.status === 0 || error.status >= 500 || (error.status >= 200 && error.status < 300);
            setUncertain(ambiguous);
            const backend = error.errors || {};
            const next = { ...(typeof backend.answers === 'object' && !Array.isArray(backend.answers) ? backend.answers : {}),
                ...(backend.applicant_email ? { [contact?.key || 'applicant_email']: backend.applicant_email } : {}),
                ...(backend.files ? { files: backend.files } : {}) };
            setMessage(ambiguous ? 'We could not confirm whether your application was received. Keep this page open and retry the same application below. The retry will not create a second entry.'
                : answerError(backend.form || backend.version || backend.submission_key || backend.detail || backend.non_field_errors) || error.message);
            focusErrors(next);
        } finally { inFlightRef.current = false; setBusy(false); }
    }
    const locked = busy || uncertain;
    return <form className="registration-panel space-y-7" onSubmit={send} noValidate aria-busy={busy}>
        <p className="text-xs leading-6 text-slate-500">Questions marked <span className="text-red-600">*</span> are required. Your application is checked before it is accepted.</p>
        {recovered.submission_key && <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">An earlier attempt may have been received. Re-enter the same answers and files to retry safely. If the form or your answers have changed, contact the organisers before starting another application.</p>}
        {(message || Object.values(errors).some(Boolean)) && <section ref={errorRef} tabIndex={-1} className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-900" role="alert"><h2 className="text-base font-semibold">{uncertain ? 'Confirmation not yet received' : 'Please check your application'}</h2>{message && <p className="mt-2 text-sm leading-7">{message}</p>}{Object.values(errors).some(Boolean) && <ul className="mt-2 space-y-1 text-sm">{Object.entries(errors).filter(([, value]) => value).map(([key, value]) => <li key={key}>{fields.find(field => field.key === key)?.label || (key === 'applicant_email' ? 'Contact email' : 'Files')}: {answerError(value)}</li>)}</ul>}</section>}
        <fieldset disabled={locked || unsupported} className="min-w-0 space-y-7">
            {!contact && <div><label htmlFor="application-contact-email" className="mb-3 block text-sm font-semibold text-primary-900">Email for this application <span aria-hidden="true" className="text-red-600">*</span></label><input id="application-contact-email" type="email" autoComplete="email" required className="registration-control" value={email} onChange={event => { setEmail(event.target.value); setDirty(true); }} aria-invalid={!!errors.applicant_email || undefined} aria-describedby="application-contact-help" /><p id="application-contact-help" className={errors.applicant_email ? 'registration-error' : 'mt-2 text-xs text-slate-500'}>{answerError(errors.applicant_email) || 'We will use this address to identify your application.'}</p></div>}
            {fields.map((field, index) => <DynamicQuestion key={field.key} field={field} index={index} value={answers[field.key]} file={files[field.key]} contact={contact?.key === field.key} error={answerError(errors[field.key])} onChange={value => edit(field.key, value)} onFile={file => {
                setFiles(previous => { const next = { ...previous }; if (file) next[field.key] = file; else delete next[field.key]; return next; });
                setDirty(true); setErrors(previous => ({ ...previous, [field.key]: '', files: '' }));
            }} />)}
        </fieldset>
        {unsupported && <p className="registration-error" role="alert">This form includes an unsupported question. Please contact the organisers.</p>}
        {busy && <div role="status" className="space-y-3 rounded-xl bg-primary-50 p-4 text-sm text-primary-800"><p>{progress === 100 ? 'Upload complete. Waiting for server confirmation…' : progress == null ? 'Sending your application…' : `Sending your application… ${progress}%`}</p><progress aria-label="Application upload progress" max="100" value={progress ?? undefined} className="h-2 w-full accent-primary-700" /><p className="text-xs">Please keep this page open. A reference number will appear after confirmation.</p></div>}
        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-6"><p className="max-w-md text-xs leading-6 text-slate-500">Submitting does not confirm selection or verify payment. The organisers will review your application.</p><button type="submit" disabled={busy || unsupported} className="btn-primary disabled:cursor-not-allowed disabled:opacity-50">{busy ? 'Processing…' : uncertain ? 'Retry same application' : 'Submit application'} <span aria-hidden="true">→</span></button></div>
        {message && !uncertain && <button type="button" className="text-sm font-semibold text-primary-700 underline underline-offset-4" onClick={() => { if (window.confirm('Reload the latest form? Unsaved answers and selected files will be cleared.')) onReload(); }}>Reload registration details</button>}
    </form>;
}
