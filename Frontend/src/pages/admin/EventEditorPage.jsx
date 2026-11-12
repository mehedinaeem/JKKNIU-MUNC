import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import useAdminAuth from '../../hooks/useAdminAuth';
import useResource from '../../hooks/useResource';
import useUnsavedChanges from '../../hooks/useUnsavedChanges';
import { api } from '../../services/api';
import { Button, Control, ErrorNotice, Loading, Notice, PageHeader, StatusBadge } from '../../components/admin/AdminUI';
import { slugify, toApiDate, toDhakaInput } from '../../components/admin/adminUtils';

const blank = { title: '', slug: '', short_description: '', description: '', event_type: '', venue: '', start_date: '', end_date: '', registration_start: '', registration_end: '', status: 'draft', cover_image: '' };
const dateFields = ['start_date', 'end_date', 'registration_start', 'registration_end'];
function EventEditor({ initial }) {
    const { isSuper, canManage } = useAdminAuth();
    const navigate = useNavigate();
    const [form, setForm] = useState(() => ({ ...blank, ...initial, ...Object.fromEntries(dateFields.map(key => [key, toDhakaInput(initial?.[key])])) }));
    const [baseline, setBaseline] = useState(JSON.stringify(form));
    const [slugEdited, setSlugEdited] = useState(!!initial);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState('');
    const canEdit = canManage && (initial || isSuper);
    useUnsavedChanges(!!canEdit && JSON.stringify(form) !== baseline);
    function change(key, value) {
        setForm(previous => ({ ...previous, [key]: value, ...(key === 'title' && !slugEdited ? { slug: slugify(value) } : {}) }));
        setNotice('');
    }
    async function save(event) {
        event.preventDefault(); setBusy(true); setError(null); setNotice('');
        try {
            const payload = Object.fromEntries(Object.keys(blank).map(key => [key, dateFields.includes(key) ? toApiDate(form[key]) : form[key]]));
            const saved = initial ? await api.patch(`/admin/events/${initial.id}/`, payload) : await api.post('/admin/events/', payload);
            if (!initial) navigate(`/admin/events/${saved.id}`, { replace: true });
            else { setBaseline(JSON.stringify(form)); setNotice('Event changes saved.'); }
        } catch (failure) { setError(failure); } finally { setBusy(false); }
    }
    if (!canEdit && !initial) return <PageHeader title="Access denied" description="Only a Super Admin can create events. You can manage events that have been assigned to you." />;
    const errors = error?.errors || {};
    return <><PageHeader title={initial ? (canEdit ? 'Edit event' : 'Event details') : 'Create an event'} description="Keep your event information and registration window up to date.">{initial && <StatusBadge status={form.status} />}</PageHeader><Link className="mb-5 inline-block text-sm font-semibold text-primary-600" to="/admin/events">← Back to events</Link><Notice>{notice}</Notice><ErrorNotice error={error} />
        <form onSubmit={save} className="admin-panel max-w-4xl" aria-busy={busy}>
            <fieldset disabled={busy || !canEdit} className="space-y-6"><div className="grid gap-5 sm:grid-cols-2"><Control label="Event title" value={form.title} onChange={event => change('title', event.target.value)} error={errors.title} required maxLength={255} /><Control label="Event slug" value={form.slug} onChange={event => { setSlugEdited(true); change('slug', event.target.value); }} error={errors.slug} required maxLength={255} hint="A unique, stable name for this event's link." /><Control label="Event type" placeholder="Conference, workshop, recruitment…" value={form.event_type} onChange={event => change('event_type', event.target.value)} error={errors.event_type} required maxLength={100} /><Control label="Venue" value={form.venue} onChange={event => change('venue', event.target.value)} error={errors.venue} maxLength={255} /></div>
                <Control as="textarea" rows={2} label="Short description" value={form.short_description} onChange={event => change('short_description', event.target.value)} error={errors.short_description} maxLength={500} /><Control as="textarea" rows={6} label="Full description" value={form.description} onChange={event => change('description', event.target.value)} error={errors.description} />
                <div className="grid gap-5 sm:grid-cols-2">{[['start_date', 'Event starts'], ['end_date', 'Event ends'], ['registration_start', 'Registration opens'], ['registration_end', 'Registration closes']].map(([key, label]) => <Control key={key} type="datetime-local" label={`${label} (Asia/Dhaka)`} value={form[key]} onChange={event => change(key, event.target.value)} error={errors[key]} required={key === 'start_date'} />)}<Control label="Status" as="select" value={form.status} onChange={event => change('status', event.target.value)} error={errors.status}>{['draft', 'published', 'completed', 'cancelled'].map(status => <option key={status} value={status}>{status.charAt(0).toUpperCase() + status.slice(1)}</option>)}</Control><Control label="Cover image URL" type="url" value={form.cover_image} onChange={event => change('cover_image', event.target.value)} error={errors.cover_image} hint="Use a hosted image URL. Existing archive images are not changed." /></div>
            </fieldset><div className="mt-8 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">{canEdit && <Button type="submit" disabled={busy}>{busy ? 'Saving…' : initial ? 'Save event' : 'Create event'}</Button>}{initial && canManage && <Link className="admin-button admin-button-secondary" to={`/admin/forms?event=${initial.id}`}>Registration forms →</Link>}{!canManage && <p className="text-sm text-slate-500">Your reviewer role provides read-only event access.</p>}</div>
        </form></>;
}
export default function EventEditorPage() {
    const { id } = useParams();
    const resource = useResource(id ? `/admin/events/${id}/` : null);
    if (resource.loading) return <Loading label="Loading event…" />;
    if (resource.error) return <ErrorNotice error={resource.error} onRetry={resource.reload} />;
    return <EventEditor key={id || 'new'} initial={resource.data || undefined} />;
}
