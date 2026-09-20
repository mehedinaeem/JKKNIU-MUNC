import { useMemo, useState } from 'react';
import { galleryImages, galleryEvents, galleryYears, galleryCategories } from '../data/gallery';
import GalleryTile from '../components/gallery/GalleryTile';
import GalleryLightbox from '../components/gallery/GalleryLightbox';
import '../components/events/events.css';
import '../components/gallery/gallery.css';

const initialFilters = { search: '', year: '', category: '', event: '' };
const batchSize = 24;

export default function GalleryPage() {
    const [filters, setFilters] = useState(initialFilters);
    const [limit, setLimit] = useState(batchSize);
    const [active, setActive] = useState(null);
    const filtered = useMemo(() => galleryImages.flatMap(item => {
        const query = filters.search.trim().toLocaleLowerCase();
        const event = item.sourceEvents.find(source => (!filters.year || String(source.year) === filters.year)
            && (!filters.category || source.category === filters.category)
            && (!filters.event || source.id === filters.event)
            && (!query || [source.title, source.category, source.date, source.shortDescription, source.fullDescription].some(value => value?.toLocaleLowerCase().includes(query))));
        return event ? [{ ...item, event }] : [];
    }), [filters]);
    function changeFilter(key, value) {
        setFilters(previous => ({ ...previous, [key]: value }));
        setLimit(batchSize);
    }
    function reset() { setFilters(initialFilters); setLimit(batchSize); }
    const visible = filtered.slice(0, limit);
    const hasFilters = Object.values(filters).some(Boolean);

    return <div className="events-page gallery-page pt-24">
        <header className="event-hero">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 motion-safe:animate-fade-in-up">
                <p className="text-accent-400 text-xs uppercase tracking-[.2em] font-semibold mb-4">JKKNIU Model United Nations Club</p>
                <h1 className="text-4xl md:text-6xl text-white font-bold">Our story <span className="text-accent-400">in pictures</span></h1>
                <p className="text-slate-300 mt-5 max-w-2xl leading-relaxed">Explore photographs and artwork from the club’s event archive. Open an image to discover the event behind it.</p>
                <p className="text-sm text-slate-300 mt-6"><strong className="text-accent-400">{galleryImages.length}</strong> unique images <span className="mx-3" aria-hidden="true">/</span><strong className="text-accent-400">{galleryEvents.length}</strong> event records</p>
            </div>
        </header>
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16" aria-label="Photo gallery">
            <div className="event-filters">
                <label className="event-filter-label">Search events or photos
                    <input type="search" placeholder="Search the collection…" value={filters.search} onChange={e => changeFilter('search', e.target.value)} />
                </label>
                <details className="gallery-filter-options mt-4">
                    <summary className="text-sm text-primary-900 font-semibold cursor-pointer py-3">Filter collection{hasFilters ? ' · Filters active' : ''}</summary>
                    <div className="grid gap-4 md:grid-cols-3 pt-3">
                        <label className="event-filter-label">Year<select aria-label="Year" value={filters.year} onChange={e => changeFilter('year', e.target.value)}><option value="">All Years</option>{galleryYears.map(year => <option key={year}>{year}</option>)}</select></label>
                        <label className="event-filter-label">Category<select aria-label="Category" value={filters.category} onChange={e => changeFilter('category', e.target.value)}><option value="">All Categories</option>{galleryCategories.map(category => <option key={category}>{category}</option>)}</select></label>
                        <label className="event-filter-label">Event<select aria-label="Event" value={filters.event} onChange={e => changeFilter('event', e.target.value)}><option value="">All Events</option>{galleryEvents.map(event => <option key={event.id} value={event.id}>{event.title}</option>)}</select></label>
                    </div>
                </details>
                {hasFilters && <button className="event-reset mt-2" onClick={reset}>Reset filters ↺</button>}
            </div>
            <p role="status" aria-live="polite" className="text-sm text-gray-600 py-6">Showing {visible.length} of {filtered.length} images</p>
            <div key={JSON.stringify(filters)} className="gallery-main-grid">
                {visible.map((item, index) => <GalleryTile key={item.id} item={item} index={index} onOpen={() => setActive(index)} />)}
            </div>
            {!filtered.length && <div className="text-center py-16"><h2 className="text-2xl text-primary-900">No images found</h2><p className="text-gray-600 mt-3 mb-6">Try another event, year or keyword.</p><button className="btn-primary" onClick={reset}>Clear filters</button></div>}
            {limit < filtered.length && <div className="text-center mt-10"><button className="btn-primary" onClick={() => setLimit(value => value + batchSize)}>Load more images</button></div>}
        </section>
        {active !== null && <GalleryLightbox items={filtered} initialIndex={active} onClose={() => setActive(null)} />}
    </div>;
}
