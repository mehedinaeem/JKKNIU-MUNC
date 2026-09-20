import { useEffect, useRef } from 'react';

export default function GalleryTile({ item, index, onOpen }) {
    const ref = useRef(null);
    useEffect(() => {
        const element = ref.current;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return;
        element.classList.add('event-awaiting');
        const observer = new IntersectionObserver(([entry]) => {
            if (!entry.isIntersecting) return;
            element.classList.remove('event-awaiting');
            element.classList.add('event-revealed');
            observer.disconnect();
        }, { threshold: .08 });
        observer.observe(element);
        return () => observer.disconnect();
    }, []);
    const event = item.event;
    return <figure ref={ref} className="gallery-tile" style={{ '--reveal-delay': `${index % 4 * 50}ms` }}>
        <button className="gallery-photo" onClick={onOpen} aria-label={`Open image: ${event.title}`} aria-haspopup="dialog">
            <img src={item.src} alt={event.title} loading="lazy" decoding="async" />
            <span className="gallery-photo-overlay" aria-hidden="true"><span className="gallery-expand-icon">↗</span></span>
        </button>
    </figure>;
}
