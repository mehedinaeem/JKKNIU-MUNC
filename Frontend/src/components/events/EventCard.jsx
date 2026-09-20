import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import EventImage from './EventImage';
import { displayDate } from './eventUtils';

export default function EventCard({ event, index }) {
    const ref = useRef(null);
    useEffect(() => {
        const element = ref.current;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return;
        element.classList.add('event-awaiting');
        const observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) {
                element.classList.remove('event-awaiting');
                element.classList.add('event-revealed');
                observer.disconnect();
            }
        }, { threshold: 0.08 });
        observer.observe(element);
        return () => observer.disconnect();
    }, []);
    return (
        <article ref={ref} className="event-reveal" style={{ '--reveal-delay': `${index % 3 * 60}ms` }}>
            <Link className="event-card group" to={`/events/${event.slug}`} aria-label={`View details: ${event.title}`}>
                <div className="event-card-image">
                    <EventImage src={event.cardDesktop || event.cardMobile} mobile={event.cardMobile} cover={event.coverImage} alt={event.title} />
                    <span className="event-year">{event.year}</span>
                </div>
                <div className="event-card-body">
                    <span className="event-category">{event.category}</span>
                    <p className="text-sm text-gray-500 mt-3">{displayDate(event)}</p>
                    <h2 className="text-lg font-semibold text-primary-900 mt-2 group-hover:text-primary-600 transition-colors">{event.title}</h2>
                    {event.shortDescription && <p className="text-sm leading-relaxed text-gray-600 mt-3 line-clamp-3">{event.shortDescription}</p>}
                    <span className="event-card-action">View details <span aria-hidden="true">↗</span></span>
                </div>
            </Link>
        </article>
    );
}
