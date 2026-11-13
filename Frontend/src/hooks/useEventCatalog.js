import { useEffect, useMemo, useState } from 'react';
import { events } from '../data/events';
import { mergeEventCatalog, splitEventCatalog } from '../services/eventCatalog';
import useResource from './useResource';

export default function useEventCatalog() {
    const remote = useResource('/events/', true, true);
    const [now, setNow] = useState(() => Date.now());
    const catalog = useMemo(() => mergeEventCatalog(events, remote.data), [remote.data]);
    useEffect(() => {
        const boundaries = catalog.flatMap(event => [event.startsAt, event.endsAt, event.registrationStartsAt, event.registrationEndsAt])
            .filter(Boolean).map(value => new Date(value).getTime()).filter(value => value > now);
        const delay = Math.min(60000, Math.max(1, Math.min(...boundaries) - now));
        const tick = () => setNow(Date.now());
        const timer = window.setTimeout(tick, delay);
        window.addEventListener('focus', tick);
        document.addEventListener('visibilitychange', tick);
        return () => {
            window.clearTimeout(timer);
            window.removeEventListener('focus', tick);
            document.removeEventListener('visibilitychange', tick);
        };
    }, [catalog, now]);
    return { ...remote, catalog, ...splitEventCatalog(catalog, now) };
}
