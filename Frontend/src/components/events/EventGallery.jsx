import { useState } from 'react';
import EventImage from './EventImage';
import EventLightbox from './EventLightbox';

export default function EventGallery({ images, title }) {
    const [active, setActive] = useState(null);
    if (!images?.length) return null;
    return <section className="mt-8" aria-labelledby="event-gallery-title">
        <h3 id="event-gallery-title" className="text-xl text-primary-900 mb-4">In pictures <span className="text-sm font-normal text-gray-500">({images.length})</span></h3>
        <div className="event-gallery-grid">
            {images.map((src, index) => <button key={src} onClick={() => setActive(index)} aria-label={`Open gallery image ${index + 1}`} aria-haspopup="dialog">
                <EventImage src={src} alt={`${title} — image ${index + 1}`} />
            </button>)}
        </div>
        {active !== null && <EventLightbox images={images} initialIndex={active} title={title} onClose={() => setActive(null)} />}
    </section>;
}
