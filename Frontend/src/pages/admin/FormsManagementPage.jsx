import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../../services/api';
import useResource from '../../hooks/useResource';
import useAdminAuth from '../../hooks/useAdminAuth';
import { Button, Control, Dialog, EmptyState, ErrorNotice, Loading, PageHeader, StatusBadge } from '../../components/admin/AdminUI';
import { displayDate, slugify } from '../../components/admin/adminUtils';

function CreateFormDialog({ events, selectedEvent, onClose }) {
    const navigate = useNavigate();
    const [form, setForm] = useState({ event: selectedEvent || String(events[0]?.id || ''), title: '', slug: '', form_type: 'event-registration' });
    const [slugEdited, setSlugEdited] = useState(false);
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    async function create(event) {
        event.preventDefault(); setBusy(true); setError(null);
        try {
            const saved = await api.post('/admin/forms/', { ...form, event: Number(form.event), fields: [] });
            navigate(`/admin/forms/${saved.id}`);
        } catch (failure) { setError(failure); } finally { setBusy(false); }
    }
    const errors = error?.errors || {};
    return <Dialog title="Create a registration form" description="Choose an event and give your form a name. You can add questions and set registration details next." onClose={onClose} busy={busy}><ErrorNotice error={error} /><form onSubmit={create} className="space-y-5"><fieldset disabled={busy} className="space-y-5"><Control label="Event" as="select" required value={form.event} error={errors.event} onChange={event => setForm({ ...form, event: event.target.value })}><option value="">Choose an event</option>{events.map(event => <option key={event.id} value={event.id}>{event.title}</option>)}</Control><Control label="Form title" required maxLength={255} value={form.title} error={errors.title} onChange={event => setForm({ ...form, title: event.target.value, ...(!slugEdited ? { slug: slugify(event.target.value) } : {}) })} placeholder="e.g. Delegate Registration" /><Control label="Form slug" required maxLength={255} value={form.slug} error={errors.slug} onChange={event => { setSlugEdited(true); setForm({ ...form, slug: event.target.value }); }} hint="Choose a unique link name using letters, numbers and hyphens." /><Control label="Form type" required maxLength={100} value={form.form_type} error={errors.form_type} onChange={event => setForm({ ...form, form_type: event.target.value })} hint="Use any type that suits your event." /></fieldset><div className="flex flex-wrap justify-end gap-2 pt-2"><Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create form'}</Button></div></form></Dialog>;
}
export default function FormsManagementPage() {
    const [params, setParams] = useSearchParams();
    const selectedEvent = params.get('event') || '';
    const events = useResource('/admin/events/', true);
    const forms = useResource(`/admin/forms/${selectedEvent ? `?event=${encodeURIComponent(selectedEvent)}` : ''}`, true);
    const { isSuper } = useAdminAuth();
    const [creating, setCreating] = useState(params.get('create') === '1');
    const [search, setSearch] = useState('');
    const [status, setStatus] = useState('');
    const [page, setPage] = useState(1);
    const filtered = forms.data?.filter(form => (!status || form.status === status) && `${form.title} ${form.form_type}`.toLowerCase().includes(search.toLowerCase())) || [];
    const totalPages = Math.max(1, Math.ceil(filtered.length / 12));
    const currentPage = Math.min(page, totalPages);
    const error = forms.error || events.error;
    const ready = !forms.loading && !events.loading && !error;
    return <><PageHeader title="Registration forms" description="A thoughtful registration starts here. Create, refine and publish forms for your club events."><Button disabled={!ready || !events.data?.length} onClick={() => setCreating(true)}>＋ Create form</Button></PageHeader><ErrorNotice error={error} onRetry={() => { forms.reload(); events.reload(); }} />
        {(forms.loading || events.loading) ? <Loading label="Loading forms…" /> : ready && <><div className="admin-panel mb-6 grid gap-4 md:grid-cols-3"><Control label="Search forms" type="search" placeholder="Search title or form type" value={search} onChange={event => { setSearch(event.target.value); setPage(1); }} /><Control label="Event" as="select" value={selectedEvent} onChange={event => setParams(event.target.value ? { event: event.target.value } : {})}><option value="">All assigned events</option>{events.data.map(event => <option key={event.id} value={event.id}>{event.title}</option>)}</Control><Control label="Form status" as="select" value={status} onChange={event => { setStatus(event.target.value); setPage(1); }}><option value="">All statuses</option>{['draft', 'published', 'closed', 'archived'].map(value => <option key={value} value={value}>{value.charAt(0).toUpperCase() + value.slice(1)}</option>)}</Control></div><p role="status" className="mb-4 text-sm text-slate-500">{filtered.length} {filtered.length === 1 ? 'form' : 'forms'}</p>
            {!filtered.length ? <EmptyState title={events.data.length ? 'Ready for your first question?' : 'No events available'} description={events.data.length ? 'Create a registration form, or change your filters to find an existing draft.' : 'A Super Admin must create and assign an event before you can build a form.'}>{events.data.length ? <Button onClick={() => setCreating(true)}>Create a form</Button> : isSuper && <Link className="admin-button admin-button-primary" to="/admin/events/new">Create an event</Link>}</EmptyState> : <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">{filtered.slice((currentPage - 1) * 12, currentPage * 12).map(form => <article key={form.id} className="admin-panel flex flex-col"><div className="mb-5 flex items-center justify-between gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-50 text-xl text-primary-600" aria-hidden="true">▤</span><StatusBadge status={form.status} /></div><p className="mb-2 text-xs font-medium text-slate-500">{events.data.find(event => event.id === form.event)?.title || 'Assigned event'}</p><h2 className="break-words text-xl text-primary-900">{form.title}</h2><p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-500">{form.description || 'Add a description to welcome your applicants.'}</p><div className="my-5 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-500"><span>{form.submission_count ?? 0} submissions</span><span>{form.accepting_submissions ? 'Open for applications' : (form.unavailable_reason || 'Not open')}</span><span>{form.field_count ?? '—'} questions</span><span>{form.capacity ? `${form.capacity} places` : 'No capacity limit'}</span><span>Closes {displayDate(form.closes_at)}</span></div><Link className="mb-3 text-sm font-semibold text-primary-700 underline" to={`/admin/sheets/${form.id}`}>View response sheet →</Link><Link className="mb-3 text-sm font-semibold text-primary-700 underline" to={`/admin/submissions?event=${form.event}&registration_form=${form.id}`}>Review applications →</Link><Link className="admin-button admin-button-secondary mt-auto w-full" to={`/admin/forms/${form.id}`}>Open form builder <span aria-hidden="true">→</span></Link></article>)}</div>}</>}
        {ready && filtered.length > 12 && <nav aria-label="Form pages" className="my-5 flex items-center justify-between gap-3"><Button variant="secondary" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>Previous</Button><span className="text-sm text-slate-500">Page {currentPage} of {totalPages}</span><Button variant="secondary" disabled={currentPage >= totalPages} onClick={() => setPage(currentPage + 1)}>Next</Button></nav>}
        {creating && ready && !!events.data.length && <CreateFormDialog events={events.data} selectedEvent={selectedEvent} onClose={() => setCreating(false)} />}
    </>;
}
