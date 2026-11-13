import { afterEach, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { splitEventCatalog, mergeEventCatalog } from '../../services/eventCatalog';
import useEventCatalog from '../../hooks/useEventCatalog';
import { api } from '../../services/api';
import UpcomingEventsSection from './UpcomingEventsSection';
vi.mock('../../services/api', () => ({ api: { publicList: vi.fn() } }));
const now = Date.parse('2026-11-12T12:00:00Z');
const raw = { id: 1, title: 'Upcoming MUN', slug: 'upcoming-mun', status: 'published', event_type: 'Conference', start_date: '2026-11-13T12:00:00Z', end_date: '2026-11-14T12:00:00Z', registration_open: true };
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

it('moves an event into past events exactly at its end, preserving its slug and data', () => {
    const catalog = mergeEventCatalog([], [raw]);
    expect(splitEventCatalog(catalog, now).upcoming[0].registrationSlug).toBe(raw.slug);
    const ongoing = splitEventCatalog(catalog, Date.parse(raw.start_date));
    expect(ongoing.upcoming).toHaveLength(1);
    expect(ongoing.upcoming[0].registrationSlug).toBeNull();
    const ended = splitEventCatalog(catalog, Date.parse(raw.end_date));
    expect(ended.upcoming).toHaveLength(0);
    expect(ended.past[0].slug).toBe(raw.slug);
    expect(ended.past[0].registrationSlug).toBeNull();
});

it('uses the start as cutoff without an end date and keeps registration closure separate', () => {
    const catalog = mergeEventCatalog([], [{ ...raw, end_date: null, registration_end: '2026-11-12T13:00:00Z' }]);
    const closed = splitEventCatalog(catalog, Date.parse('2026-11-12T14:00:00Z'));
    expect(closed.upcoming).toHaveLength(1);
    expect(closed.upcoming[0].registrationSlug).toBeNull();
    expect(splitEventCatalog(catalog, Date.parse(raw.start_date)).past).toHaveLength(1);
    const sorted = splitEventCatalog(mergeEventCatalog([], [raw, { ...raw, id: 2, slug: 'sooner', start_date: '2026-11-12T16:00:00Z', end_date: null }]), now);
    expect(sorted.upcoming.map(event => event.slug)).toEqual(['sooner', 'upcoming-mun']);
});

it('updates the page when the date passes without navigation or refresh', async () => {
    vi.useFakeTimers(); vi.setSystemTime(now);
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    api.publicList.mockResolvedValue([{ ...raw, start_date: new Date(now + 1000).toISOString(), end_date: null }]);
    function Preview() {
        const catalog = useEventCatalog();
        return <><UpcomingEventsSection events={catalog.upcoming} /><p>Past count: {catalog.past.filter(event => event.managed).length}</p></>;
    }
    await act(async () => { render(<MemoryRouter><Preview /></MemoryRouter>); });
    expect(screen.getByRole('heading', { name: 'Upcoming MUN', exact: true })).toBeVisible();
    await act(async () => { vi.advanceTimersByTime(1000); });
    expect(screen.queryByRole('heading', { name: 'Upcoming MUN', exact: true })).not.toBeInTheDocument();
    expect(screen.getByText('Past count: 1')).toBeVisible();
});
