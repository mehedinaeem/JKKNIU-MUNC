import { useEffect, useRef } from 'react';
import { Link, useParams } from 'react-router-dom';
import { events } from '../data/events';
import { eventDescriptions } from '../data/eventDescriptions';
import EventImage from '../components/events/EventImage';
import EventGallery from '../components/events/EventGallery';
import { displayDate, newestFirst } from '../components/events/eventUtils';
import '../components/events/events.css';

const detailFields = ['venue', 'mode', 'participants', 'speakers', 'guests', 'awards', 'partners', 'highlights'];
const orderedEvents = [...events].sort(newestFirst);

export default function EventDetailsPage() {
    const { slug } = useParams();
    const event = events.find(item => item.slug === slug);
    const heading = useRef(null);
    useEffect(() => {
        window.scrollTo({ top: 0, behavior: 'instant' });
        heading.current?.focus({ preventScroll: true });
        const previousTitle = document.title;
        document.title = `${event?.title || 'Event not found'} | JKKNIU MUNC`;
        return () => { document.title = previousTitle; };
    }, [slug, event]);

    if (!event) return <div className="events-page pt-24">
        <section className="section-container min-h-[60vh]">
            <h1 ref={heading} tabIndex={-1} className="section-title">Event not found</h1>
            <p className="text-gray-600 mb-8">This event link is unavailable. Browse the archive to find an event.</p>
            <Link to="/events" className="btn-primary">Back to all events</Link>
        </section>
    </div>;

    const fields = detailFields.filter(key => event[key]?.length);
    const currentIndex = orderedEvents.findIndex(item => item.id === event.id);
    const next = orderedEvents[currentIndex + 1];
    const previous = orderedEvents[currentIndex - 1];
    const sources = [
        ...(event.facebookUrl ? [{ url: event.facebookUrl, label: 'View Facebook source' }] : []),
        ...event.newsLinks.map((url, index) => ({ url, label: `Read source ${index + 1}` })),
    ];

    return <article className="events-page event-story pt-24">
        <header className="event-story-header">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <Link to="/events" className="event-back-link">← Back to all events</Link>
                <div className="mt-8 sm:mt-12 motion-safe:animate-fade-in-up">
                    <div className="flex flex-wrap gap-3 items-center mb-5">
                        <span className="event-category">{event.category}</span>
                        <span className="text-sm text-slate-300">{event.year} / Event archive</span>
                    </div>
                    <h1 ref={heading} tabIndex={-1} className="event-story-title">{event.title}</h1>
                    <p className="text-slate-300 mt-6 text-base sm:text-lg">{displayDate(event)}</p>
                </div>
            </div>
        </header>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 sm:pb-24">
            <figure className="event-story-figure">
                <EventImage key={event.id} src={event.coverImage || event.cardDesktop} alt={event.title} loading="eager" />
                <figcaption className="px-4 py-3 text-xs sm:text-sm text-gray-500 border-t border-slate-200">{event.coverImage ? 'From the event archive' : 'Event archive artwork'} · {event.year}</figcaption>
            </figure>
            <div className="event-story-layout">
                <div className="min-w-0">
                    <section aria-labelledby="event-overview-heading">
                        <p className="event-story-eyebrow">The story</p>
                        <h2 id="event-overview-heading" className="text-2xl sm:text-3xl text-primary-900 mb-6">About this event</h2>
                        <p className="text-base sm:text-lg text-slate-600 leading-[1.9]">{eventDescriptions[event.id] || event.fullDescription}</p>
                        {event.status === 'Needs verification' && <p className="event-archive-note">This entry is awaiting verification. Its title and date are retained as supplied in the archive.</p>}
                    </section>
                    {fields.length > 0 && <section className="mt-10 border-t border-slate-200 pt-8" aria-labelledby="event-details-heading">
                        <h2 id="event-details-heading" className="text-2xl text-primary-900 mb-6">Event details</h2>
                        <dl className="grid sm:grid-cols-2 gap-6">
                            {fields.map(key => <div key={key}>
                                <dt className="capitalize font-semibold text-primary-900 mb-2">{key}</dt>
                                <dd className="text-gray-600 leading-relaxed">{Array.isArray(event[key]) ? <ul className="list-disc pl-5">{event[key].map((item, index) => <li key={index}>{item}</li>)}</ul> : event[key]}</dd>
                            </div>)}
                        </dl>
                    </section>}
                    <EventGallery key={event.id} images={event.gallery} title={event.title} />
                </div>
                <aside className="event-story-sidebar" aria-label="Event information">
                    <h2 className="text-lg text-primary-900 mb-5">At a glance</h2>
                    <dl className="space-y-5">
                        {[[displayDate(event), 'Date'], [event.category, 'Category'], [event.status, 'Record status']].map(([value, label]) => value && <div key={label}>
                            <dt className="text-xs uppercase tracking-wider text-gray-500 mb-1">{label}</dt>
                            <dd className="text-sm font-medium text-primary-900">{value}</dd>
                        </div>)}
                    </dl>
                    {sources.length > 0 && <section className="border-t border-slate-200 mt-6 pt-6" aria-labelledby="event-sources-heading">
                        <h3 id="event-sources-heading" className="text-sm text-primary-900 mb-3">Original sources</h3>
                        <div className="flex flex-col gap-3">{sources.map(({ url, label }) => <a key={url} className="event-source" href={url} target="_blank" rel="noopener noreferrer">{label} <span aria-hidden="true">↗</span></a>)}</div>
                    </section>}
                </aside>
            </div>
            <nav aria-label="More events" className="event-story-navigation">
                {previous ? <Link to={`/events/${previous.slug}`}><span>← Newer event</span><strong>{previous.title}</strong></Link> : <Link to="/events"><span>← Explore the collection</span><strong>All events</strong></Link>}
                {next && <Link to={`/events/${next.slug}`}><span>Older event →</span><strong>{next.title}</strong></Link>}
            </nav>
        </div>
    </article>;
}
