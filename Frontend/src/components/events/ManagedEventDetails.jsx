import { useEffect, useRef } from 'react';
import { Link, Navigate } from 'react-router-dom';
import useResource from '../../hooks/useResource';
import { events } from '../../data/events';
import { backendEvent, historicalMatch, safeCover } from '../../services/eventCatalog';
import EventImage from './EventImage';

const moment = value => value ? new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Dhaka', day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' }).format(new Date(value)) : 'Not set';

export default function ManagedEventDetails({ slug }) {
    const event = useResource(`/events/${encodeURIComponent(slug)}/`, false, true);
    const forms = useResource(event.data ? `/events/${encodeURIComponent(slug)}/forms/` : null, true, true);
    const heading = useRef(null);
    useEffect(() => {
        const title = document.title;
        document.title = `${event.data?.title || 'Event details'} | JKKNIU MUNC`;
        heading.current?.focus({ preventScroll: true });
        window.scrollTo({ top: 0, behavior: 'instant' });
        return () => { document.title = title; };
    }, [slug, event.data]);
    // A duplicate with a different slug still resolves to the preserved archive URL.
    const canonical = event.data && backendEvent(event.data) && historicalMatch(events, backendEvent(event.data));
    if (canonical && canonical.slug !== slug) return <Navigate replace to={`/events/${canonical.slug}`} />;
    if (event.loading) return <div role="status" className="events-page min-h-[60vh] px-5 pb-16 pt-36 text-center text-primary-900">Loading event details…</div>;
    if (event.error || !backendEvent(event.data)) return <div className="events-page pt-24"><section className="section-container min-h-[60vh]"><h1 ref={heading} tabIndex={-1} className="section-title">{event.error?.status === 404 ? 'Event not found' : 'Event details unavailable'}</h1><p className="mb-6 text-slate-600">{event.error?.status === 404 ? 'This event link is unavailable.' : 'We could not load this event. Please try again shortly.'} The historical archive is still available.</p>{event.error?.status !== 404 && <button className="btn-primary mb-4 mr-4" onClick={event.reload}>Try again</button>}<Link className="btn-secondary" to="/events">Back to all events</Link></section></div>;
    const data = event.data;
    const open = forms.data?.some(form => form.accepting_submissions);
    return <article className="events-page event-story pt-24"><header className="event-story-header"><div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8"><Link className="event-back-link" to="/events">← Back to all events</Link><div className="mt-8 sm:mt-12"><span className="event-category">{data.event_type}</span><h1 ref={heading} tabIndex={-1} className="event-story-title mt-5">{data.title}</h1><p className="mt-6 text-slate-300">{moment(data.start_date)}</p>{data.short_description && <p className="mt-5 max-w-3xl text-slate-300">{data.short_description}</p>}</div></div></header><div className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 sm:pb-24 lg:px-8">{safeCover(data.cover_image) && <figure className="event-story-figure"><EventImage src={safeCover(data.cover_image)} alt={data.title} loading="eager" /></figure>}<div className="event-story-layout mt-10"><section className="min-w-0" aria-labelledby="managed-event-about"><p className="event-story-eyebrow">Join the experience</p><h2 id="managed-event-about" className="mb-6 text-2xl text-primary-900 sm:text-3xl">About this event</h2><p className="whitespace-pre-wrap break-words text-base leading-[1.9] text-slate-600">{data.description || data.short_description}</p></section><aside className="event-story-sidebar" aria-label="Event information"><h2 className="mb-5 text-lg text-primary-900">At a glance</h2><dl className="space-y-5">{[['Starts', moment(data.start_date)], ...(data.end_date ? [['Ends', moment(data.end_date)]] : []), ['Venue', data.venue || 'To be announced'], ['Category', data.event_type], ...(data.registration_end ? [['Registration deadline', moment(data.registration_end)]] : [])].map(([label, value]) => <div key={label}><dt className="mb-1 text-xs uppercase tracking-wider text-slate-500">{label}</dt><dd className="break-words text-sm font-medium text-primary-900">{value}</dd></div>)}</dl><section className="mt-6 border-t border-slate-200 pt-6" aria-label="Registration">{forms.loading ? <p role="status" className="text-sm text-slate-500">Checking registration availability…</p> : forms.error ? <><p role="status" className="text-sm leading-6 text-slate-600">Registration details are temporarily unavailable.</p><button type="button" className="mt-3 text-sm font-semibold text-primary-700 underline" onClick={forms.reload}>Retry registration details</button></> : open ? <><p className="mb-4 text-sm leading-6 text-slate-600">Registration is open. Choose the right application category to get started.</p><Link className="btn-primary block text-center" to={`/events/${encodeURIComponent(slug)}/register`}>Register now →</Link></> : <p role="status" className="text-sm leading-6 text-slate-600">{forms.data?.length ? forms.data[0].unavailable_reason || 'Registration is currently closed.' : 'Registration is not open for this event yet.'}</p>}</section></aside></div></div></article>;
}
