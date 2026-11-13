import { newestFirst } from '../components/events/eventUtils';

const normalized = value => value.normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase();
export function dhakaDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Dhaka', year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
}
export function backendEvent(event) {
    if (!event || event.status !== 'published' || typeof event.slug !== 'string' || !/^[a-zA-Z0-9_-]+$/.test(event.slug)
        || typeof event.start_date !== 'string' || typeof event.title !== 'string' || !event.title.trim() || !dhakaDate(event.start_date)) return null;
    const date = dhakaDate(event.start_date);
    return { id: `api-${event.id}`, slug: event.slug, title: event.title, year: Number(date.slice(0, 4)), date,
        endDate: event.end_date ? dhakaDate(event.end_date) : '', category: event.event_type || 'Event',
        shortDescription: event.short_description || '', fullDescription: event.description || '',
        coverImage: safeCover(event.cover_image), cardDesktop: safeCover(event.cover_image), cardMobile: '',
        registrationSlug: event.registration_open ? event.slug : null, managed: true,
        startsAt: event.start_date, endsAt: event.end_date || event.start_date,
        registrationStartsAt: event.registration_start, registrationEndsAt: event.registration_end };
}
export function safeCover(value) {
    if (typeof value !== 'string') return '';
    try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? value : ''; }
    catch { return ''; }
}
const exactIdentity = event => /^\d{4}-\d{2}-\d{2}$/.test(event.date) ? `${normalized(event.title)}:${event.date}` : null;

export function historicalMatch(historical, event) {
    return historical.find(item => item.slug === event.slug || (exactIdentity(event) && exactIdentity(item) === exactIdentity(event)));
}

export function mergeEventCatalog(historical, remote) {
    // Never mutate/import archive records into Django. Existing URLs and content win.
    const result = historical.map(event => ({ ...event }));
    const slugs = new Map(result.map(event => [event.slug, event]));
    const identities = new Map(result.map(event => [exactIdentity(event), event]).filter(([key]) => key));
    for (const raw of remote || []) {
        const event = backendEvent(raw);
        if (!event) continue;
        const existing = slugs.get(event.slug) || identities.get(exactIdentity(event));
        if (existing) {
            if (event.registrationSlug && !existing.registrationSlug) existing.registrationSlug = event.registrationSlug;
            continue;
        }
        result.push(event); slugs.set(event.slug, event);
        const identity = exactIdentity(event);
        if (identity) identities.set(identity, event);
    }
    return result.sort(newestFirst);
}


export function splitEventCatalog(catalog, now) {
    const upcoming = [], past = [];
    for (const event of catalog) {
        // Archive entries keep their original interpretation and editorial dates.
        const current = event.managed && new Date(event.endsAt).getTime() > now;
        const canRegister = current && new Date(event.startsAt).getTime() > now
            && (!event.registrationStartsAt || new Date(event.registrationStartsAt).getTime() <= now)
            && (!event.registrationEndsAt || new Date(event.registrationEndsAt).getTime() > now);
        const displayed = { ...event, registrationSlug: canRegister ? event.registrationSlug : null };
        (current ? upcoming : past).push(displayed);
    }
    upcoming.sort((a, b) => new Date(a.startsAt) - new Date(b.startsAt));
    past.sort(newestFirst);
    return { upcoming, past };
}
