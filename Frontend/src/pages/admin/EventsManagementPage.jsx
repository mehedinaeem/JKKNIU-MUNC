import { useState } from 'react';
import { Link } from 'react-router-dom';
import useAdminAuth from '../../hooks/useAdminAuth';
import useResource from '../../hooks/useResource';
import { Control, EmptyState, ErrorNotice, Loading, PageHeader, StatusBadge } from '../../components/admin/AdminUI';
import { displayDate } from '../../components/admin/adminUtils';

export default function EventsManagementPage() {
    const { isSuper, canManage } = useAdminAuth();
    const resource = useResource('/admin/events/', true);
    const [search, setSearch] = useState('');
    const events = resource.data?.filter(event => `${event.title} ${event.event_type}`.toLowerCase().includes(search.toLowerCase())) || [];
    return <><PageHeader title="Events" description="Manage the events assigned to your workspace. The historical public archive is maintained separately.">{isSuper && <Link to="/admin/events/new" className="admin-button admin-button-primary">＋ Create event</Link>}</PageHeader><ErrorNotice error={resource.error} onRetry={resource.reload} />
        {resource.loading ? <Loading label="Loading events…" /> : !resource.error && <><div className="mb-6 max-w-md"><Control label="Search events" type="search" placeholder="Search by title or event type" value={search} onChange={event => setSearch(event.target.value)} /></div><p role="status" className="mb-4 text-sm text-slate-500">{events.length} {events.length === 1 ? 'event' : 'events'}</p>
            {!events.length ? <EmptyState title="No matching events" description="Try a different search, create your first event, or ask a Super Admin to check your assignments." /> : <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">{events.map(event => <article key={event.id} className="admin-panel flex flex-col"><div className="mb-5 flex items-center justify-between gap-3"><span className="text-xs font-semibold uppercase tracking-wider text-primary-600">{event.event_type}</span><StatusBadge status={event.status} /></div><h2 className="break-words text-xl text-primary-900">{event.title}</h2><p className="mt-3 text-sm leading-6 text-slate-500">{event.short_description || 'No short description added.'}</p><p className="mb-6 mt-4 text-xs text-slate-500">{displayDate(event.start_date)}{event.venue && ` · ${event.venue}`}</p><div className="mt-auto flex flex-wrap gap-2 border-t border-slate-100 pt-4"><Link className="admin-button admin-button-secondary" to={`/admin/events/${event.id}`}>{canManage ? 'Edit event' : 'View event'}</Link>{canManage && <Link className="admin-button admin-button-ghost" to={`/admin/forms?event=${event.id}`}>Registration forms →</Link>}</div></article>)}</div>}</>}
    </>;
}
