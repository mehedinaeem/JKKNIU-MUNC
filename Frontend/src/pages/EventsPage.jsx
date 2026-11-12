import { useMemo, useState } from 'react';
import { events } from '../data/events';
import EventCard from '../components/events/EventCard';
import EventFilters from '../components/events/EventFilters';
import EventsStats from '../components/events/EventsStats';
import useResource from '../hooks/useResource';
import { mergeEventCatalog } from '../services/eventCatalog';
import '../components/events/events.css';

const initialFilters = { search: '', year: '', category: '' };

export default function EventsPage() {
    const [filters, setFilters] = useState(initialFilters);
    const remote = useResource('/events/', true, true);
    const sortedEvents = useMemo(() => mergeEventCatalog(events, remote.data), [remote.data]);
    const years = [...new Set(sortedEvents.map(event => event.year))].sort((a, b) => b - a);
    const categories = [...new Set(sortedEvents.map(event => event.category).filter(Boolean))].sort();
    const filtered = useMemo(() => {
        const query = filters.search.trim().toLocaleLowerCase();
        return sortedEvents.filter(event => (!filters.year || String(event.year) === filters.year)
            && (!filters.category || event.category === filters.category)
            && (!query || [event.title, event.shortDescription, event.fullDescription, event.category].some(value => value?.toLocaleLowerCase().includes(query))));
    }, [filters, sortedEvents]);
    return <div className="events-page pt-24 bg-slate-50">
        <section className="event-hero">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative motion-safe:animate-fade-in-up">
                <p className="text-accent-400 uppercase tracking-[.2em] text-xs font-semibold mb-4">JKKNIU Model United Nations Club</p>
                <h1 className="text-4xl md:text-6xl font-bold text-white">Events <span className="text-accent-400">Archive</span></h1>
                <p className="text-slate-300 mt-5 max-w-2xl leading-relaxed text-base sm:text-lg">Explore the conferences, workshops, competitions, training sessions and activities of JKKNIU Model United Nations Club.</p>
                <EventsStats total={sortedEvents.length} years={years.length} categories={categories.length} />
            </div>
        </section>
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16" aria-label="Browse events">
            {remote.loading && <p role="status" className="pt-6 text-sm text-slate-500">Checking current events… The historical archive is available below.</p>}
            {remote.error && <div role="status" className="flex flex-wrap items-center justify-between gap-3 pt-6 text-sm text-slate-600"><p>Current events are temporarily unavailable. You can still browse the historical archive.</p><button type="button" className="font-semibold text-primary-700 underline underline-offset-4" onClick={remote.reload}>Retry current events</button></div>}
            <EventFilters filters={filters} onChange={(key, value) => setFilters(previous => ({ ...previous, [key]: value }))} years={years} categories={categories} onReset={() => setFilters(initialFilters)} />
            <div className="flex items-center justify-between gap-4 py-7">
                <p role="status" aria-live="polite" aria-atomic="true" className="font-semibold text-primary-900">{filtered.length} {filtered.length === 1 ? 'Event' : 'Events'}</p>
                <p className="text-sm text-gray-500">Newest first</p>
            </div>
            <div key={JSON.stringify(filters)} className="event-grid grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filtered.map((event, index) => <EventCard key={event.slug} event={event} index={index} />)}
                {!filtered.length && <div className="col-span-full text-center py-20 bg-white border border-slate-200 rounded-2xl">
                    <h2 className="text-2xl text-primary-900">No events found</h2>
                    <p className="text-gray-500 mt-3 mb-6">Try another keyword, year or category.</p>
                    <button className="btn-primary" onClick={() => setFilters(initialFilters)}>Reset filters</button>
                </div>}
            </div>
        </section>
    </div>;
}
