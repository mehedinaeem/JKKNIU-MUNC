import { useState } from 'react';
import EventDialog from './EventDialog';
import EventImage from './EventImage';

export default function EventLightbox({ images, initialIndex, title, onClose }) {
    const [index, setIndex] = useState(initialIndex);
    const move = delta => setIndex(value => (value + delta + images.length) % images.length);
    return <EventDialog labelId="event-lightbox-title" className="event-lightbox" onClose={onClose}
        onKeyDown={e => {
            if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); move(e.key === 'ArrowRight' ? 1 : -1); }
        }}>
        <h2 id="event-lightbox-title" className="sr-only">{title} — gallery</h2>
        <EventImage key={images[index]} src={images[index]} alt={`${title} — image ${index + 1}`} loading="eager" className="event-lightbox-image" />
        <div className="event-lightbox-controls">
            <button aria-label="Previous image" onClick={() => move(-1)} disabled={images.length < 2}>←</button>
            <p aria-live="polite">{index + 1} / {images.length}</p>
            <button aria-label="Next image" onClick={() => move(1)} disabled={images.length < 2}>→</button>
        </div>
    </EventDialog>;
}
