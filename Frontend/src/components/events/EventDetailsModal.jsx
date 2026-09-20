import EventDialog from './EventDialog';
import EventImage from './EventImage';
import EventGallery from './EventGallery';
import { displayDate } from './eventUtils';

const detailFields = ['venue', 'mode', 'participants', 'speakers', 'guests', 'awards', 'partners', 'highlights'];

export default function EventDetailsModal({ event, onClose }) {
    const availableFields = detailFields.filter(key => event[key]?.length);
    return <EventDialog labelId="event-detail-title" onClose={onClose}>
        <EventImage src={event.coverImage || event.cardDesktop} alt={event.title} loading="eager" className="event-detail-cover" />
        <div className="p-5 sm:p-8">
            <div className="flex flex-wrap gap-2 items-center mb-4">
                <span className="event-category">{event.category}</span>
                {event.status && <span className="text-xs rounded-full bg-gray-100 text-gray-600 px-3 py-1">{event.status}</span>}
            </div>
            <h2 id="event-detail-title" className="text-2xl sm:text-3xl text-primary-900 leading-snug pr-2">{event.title}</h2>
            <p className="text-gray-500 mt-3">{displayDate(event)}</p>
            {(event.fullDescription || event.shortDescription) && <p className="text-gray-600 leading-relaxed whitespace-pre-line mt-6">{event.fullDescription || event.shortDescription}</p>}
            {availableFields.length > 0 && <dl className="grid sm:grid-cols-2 gap-5 mt-6">
                {availableFields.map(key => <div key={key}>
                    <dt className="capitalize font-semibold text-primary-900 mb-1">{key}</dt>
                    <dd className="text-gray-600">{Array.isArray(event[key]) ? <ul className="list-disc pl-5">{event[key].map((item, index) => <li key={index}>{item}</li>)}</ul> : event[key]}</dd>
                </div>)}
            </dl>}
            <EventGallery images={event.gallery} title={event.title} />
            {(event.facebookUrl || event.newsLinks?.length > 0) && <section className="mt-8 border-t pt-6">
                <h3 className="text-lg text-primary-900 mb-3">Sources & further reading</h3>
                <div className="flex flex-wrap gap-3">
                    {event.facebookUrl && <a className="event-source" href={event.facebookUrl} target="_blank" rel="noopener noreferrer">Facebook source ↗</a>}
                    {event.newsLinks?.map((url, index) => <a className="event-source" key={url} href={url} target="_blank" rel="noopener noreferrer">Source {index + 1} ↗</a>)}
                </div>
            </section>}
        </div>
    </EventDialog>;
}
