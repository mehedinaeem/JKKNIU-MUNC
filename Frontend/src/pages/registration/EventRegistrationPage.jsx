import { Link, useParams } from 'react-router-dom';
import useResource from '../../hooks/useResource';
import { RegistrationHero, RegistrationLoading, RegistrationUnavailable } from '../../components/registration/RegistrationUI';
import '../../components/registration/registration.css';

export default function EventRegistrationPage() {
    const { slug } = useParams();
    const event = useResource(`/events/${encodeURIComponent(slug)}/`, false, true);
    const forms = useResource(`/events/${encodeURIComponent(slug)}/forms/`, true, true);
    const loading = event.loading || forms.loading;
    const error = event.error || forms.error;
    return <div className="registration-page min-h-[70vh] bg-slate-50 pt-24"><RegistrationHero title={event.data?.title || 'Event registration'}><p>Choose your registration category and take the next step with JKKNIU MUNC.</p>{event.data?.venue && <p className="mt-2 text-sm text-accent-200">{event.data.venue}</p>}</RegistrationHero><main className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-14">
        {loading ? <RegistrationLoading /> : error ? <RegistrationUnavailable error={error} onRetry={() => { event.reload(); forms.reload(); }} /> : !forms.data?.length ? <RegistrationUnavailable reason="There are no published registration forms for this event right now. Please check again later or contact the organisers." /> : <><div className="mb-7"><p className="text-xs font-semibold uppercase tracking-[.18em] text-primary-600">Find your place</p><h2 className="mt-2 text-2xl text-primary-900">How would you like to participate?</h2></div><div className="grid gap-6 md:grid-cols-2">{forms.data.map(form => <article key={form.id} className="registration-panel flex flex-col"><div className="mb-6 flex items-center justify-between gap-3"><span aria-hidden="true" className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-50 text-2xl text-primary-700">▤</span><span className={`rounded-full px-3 py-1 text-xs font-semibold ${form.accepting_submissions ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-900'}`}>{form.accepting_submissions ? 'Open for applications' : 'Not accepting applications'}</span></div><h3 className="text-xl text-primary-900">{form.schema.title}</h3><p className="mb-6 mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-500">{form.schema.description}</p>{!form.accepting_submissions && <p className="mb-5 text-sm text-amber-800">{form.unavailable_reason || 'Registration is currently unavailable.'}</p>}<Link className="btn-primary mt-auto text-center" to={`/events/${encodeURIComponent(slug)}/register/${encodeURIComponent(form.slug)}`}>{form.accepting_submissions ? 'Start application' : 'View registration details'} <span aria-hidden="true">→</span></Link></article>)}</div><p className="mt-8 text-sm leading-7 text-slate-500">Each category has its own application. Please review the questions and event information before submitting.</p></>}
    </main></div>;
}
