import { useState } from 'react';
import { Link } from 'react-router-dom';
import EventDialog from '../events/EventDialog';
import { displayDate } from '../events/eventUtils';

export default function GalleryLightbox({ items, initialIndex, onClose }) {
    const [index, setIndex] = useState(initialIndex);
    const move = delta => setIndex(current => (current + delta + items.length) % items.length);
    const item = items[index];
    const event = item.event;
    return <EventDialog labelId="gallery-lightbox-title" className="event-lightbox gallery-lightbox" onClose={onClose}
        onKeyDown={e => {
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); move(e.key === 'ArrowRight' ? 1 : -1); }
        }}>
        <img key={item.id} className="gallery-large-image" src={item.src} alt={event.title} decoding="async" />
        <div className="gallery-lightbox-caption">
            <h2 id="gallery-lightbox-title" className="text-base sm:text-xl font-semibold">{event.title}</h2>
            <p className="text-sm text-slate-300 mt-2">{displayDate(event)} · {event.category}</p>
            <Link className="inline-flex min-h-11 items-center text-accent-300 mt-2" to={`/events/${event.slug}`}>View Event →</Link>
            {item.sourceEvents.length > 1 && <details className="mt-2 text-sm text-slate-300">
                <summary className="cursor-pointer py-2">Also appears in {item.sourceEvents.length - 1} other event records</summary>
                <ul className="space-y-3 py-3">{item.sourceEvents.filter(source => source.id !== event.id).map(source => <li key={source.id}><Link className="underline underline-offset-4" to={`/events/${source.slug}`}>{source.title}</Link></li>)}</ul>
            </details>}
        </div>
        <div className="event-lightbox-controls">
            <button aria-label="Previous image" onClick={() => move(-1)} disabled={items.length < 2}>←</button>
            <p role="status" aria-live="polite">{index + 1} / {items.length}</p>
            <button aria-label="Next image" onClick={() => move(1)} disabled={items.length < 2}>→</button>
        </div>
    </EventDialog>;
}
