import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import useResource from '../../hooks/useResource';
import RegistrationForm from '../../components/registration/RegistrationForm';
import { RegistrationHero, RegistrationLoading, RegistrationUnavailable } from '../../components/registration/RegistrationUI';
import { readAttempt } from '../../services/registration';
import '../../components/registration/registration.css';

function PublishedRegistration({ definition, eventSlug, onReload }) {
    const [receipt] = useState(() => readAttempt(eventSlug, definition.slug));
    if (receipt.reference_number) return <Navigate replace to={`/events/${encodeURIComponent(eventSlug)}/register/${encodeURIComponent(definition.slug)}/confirmation`} />;
    if (!definition.accepting_submissions) return <RegistrationUnavailable reason={definition.unavailable_reason || 'This form is not accepting applications.'} />;
    return <RegistrationForm definition={definition} eventSlug={eventSlug} onReload={onReload} />;
}
export default function EventRegistrationFormPage() {
    const { slug, formSlug } = useParams();
    const event = useResource(`/events/${encodeURIComponent(slug)}/`, false, true);
    const form = useResource(`/forms/${encodeURIComponent(formSlug)}/`, false, true);
    const matches = form.data?.event_slug === slug;
    const error = event.error || form.error;
    return <div className="registration-page min-h-[70vh] bg-slate-50 pt-24"><RegistrationHero title={matches ? form.data.schema.title : 'Event application'} eyebrow={event.data?.title || 'JKKNIU MUNC registration'}>{matches && <p className="whitespace-pre-wrap">{form.data.schema.description}</p>}</RegistrationHero><main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-12"><Link to={`/events/${encodeURIComponent(slug)}/register`} className="mb-6 inline-block text-sm font-semibold text-primary-700">← All registration categories</Link>
        {event.loading || form.loading ? <RegistrationLoading /> : error ? <RegistrationUnavailable error={error} onRetry={() => { event.reload(); form.reload(); }} /> : !matches ? <RegistrationUnavailable reason="This form is not available for the selected event." /> : <PublishedRegistration key={`${form.data.id}:${form.data.version}`} definition={form.data} eventSlug={slug} onReload={form.reload} />}
    </main></div>;
}
