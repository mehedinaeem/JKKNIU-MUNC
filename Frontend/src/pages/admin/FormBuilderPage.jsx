import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import useResource from '../../hooks/useResource';
import useUnsavedChanges from '../../hooks/useUnsavedChanges';
import { api } from '../../services/api';
import { Button, Control, Dialog, EmptyState, ErrorNotice, Loading, Notice, PageHeader, StatusBadge } from '../../components/admin/AdminUI';
import { errorText, slugify, toDhakaInput } from '../../components/admin/adminUtils';
import FieldPalette from '../../components/form-builder/FieldPalette';
import FieldEditor from '../../components/form-builder/FieldEditor';
import FormPreview from '../../components/form-builder/FormPreview';
import { formPayload, newField } from '../../components/form-builder/schema';

function editableForm(data) {
    return { ...data, opens_at: toDhakaInput(data.opens_at), closes_at: toDhakaInput(data.closes_at), capacity: data.capacity ?? '',
        fields: [...(data.fields || [])].sort((a, b) => a.display_order - b.display_order) };
}
function DuplicateDialog({ form, busy, error, onClose, onDuplicate }) {
    const [title, setTitle] = useState(`${form.title} (copy)`);
    const [slug, setSlug] = useState(`${slugify(form.slug)}-copy`);
    const events = useResource('/admin/events/', true);
    const [eventId, setEventId] = useState(String(form.event));
    return <Dialog title="Duplicate form" description="Your current draft will be saved, then copied into a new independent draft. Existing responses stay with the original form." onClose={onClose} busy={busy}><form className="space-y-5" onSubmit={event => { event.preventDefault(); onDuplicate({ title, slug, event: Number(eventId) }); }}><ErrorNotice error={error || events.error} /><Control label="Destination event" as="select" value={eventId} disabled={busy || events.loading} error={error?.errors?.event} onChange={event => setEventId(event.target.value)}>{events.data?.map(event => <option key={event.id} value={event.id}>{event.title}</option>)}</Control><p className="admin-hint">Copies to a different event start with no opening or closing dates. Responses and published versions are never copied.</p><Control label="New form title" required maxLength={255} disabled={busy} value={title} error={error?.errors?.title} onChange={event => setTitle(event.target.value)} /><Control label="New form slug" required maxLength={255} disabled={busy} value={slug} error={error?.errors?.slug} onChange={event => setSlug(event.target.value)} /><div className="flex flex-wrap justify-end gap-2"><Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? 'Duplicating…' : 'Create duplicate'}</Button></div></form></Dialog>;
}
function FormBuilder({ initial }) {
    const navigate = useNavigate();
    const [form, setForm] = useState(() => editableForm(initial));
    const [baseline, setBaseline] = useState(() => JSON.stringify(formPayload(editableForm(initial))));
    const [expanded, setExpanded] = useState(initial.fields?.[0]?.key);
    const [palette, setPalette] = useState(false);
    const [preview, setPreview] = useState(false);
    const [confirmation, setConfirmation] = useState(null);
    const [duplicate, setDuplicate] = useState(false);
    const [duplicateError, setDuplicateError] = useState(null);
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState('');
    const [announcement, setAnnouncement] = useState('');
    const [busy, setBusy] = useState('');
    const dirty = JSON.stringify(formPayload(form)) !== baseline;
    useUnsavedChanges(dirty);
    const errors = error?.errors || {};
    function change(key, value) { setForm(previous => ({ ...previous, [key]: value })); setNotice(''); }
    function fieldChange(key, value) {
        setForm(previous => ({ ...previous, fields: previous.fields.map(field => field.key === key ? value : field) }));
        setNotice('');
    }
    function add(type) {
        const field = newField(type);
        setForm(previous => ({ ...previous, fields: [...previous.fields, field] }));
        setExpanded(field.key); setPalette(false); setNotice(''); setError(null);
        setAnnouncement(`Question ${form.fields.length + 1} added.`);
        window.requestAnimationFrame(() => document.getElementById(`editor-${field.key}`)?.querySelector('input')?.focus());
    }
    function move(index, direction) {
        const fields = [...form.fields];
        [fields[index], fields[index + direction]] = [fields[index + direction], fields[index]];
        change('fields', fields); setError(null);
        setAnnouncement(`Question moved to position ${index + direction + 1}.`);
    }
    function report(failure, draftWasSaved = false) {
        setError(failure);
        if (draftWasSaved) setNotice('Your draft was saved, but the next action did not complete.');
        const fieldErrors = failure.errors?.fields;
        if (Array.isArray(fieldErrors)) {
            const index = fieldErrors.findIndex(value => value && Object.keys(value).length > 0);
            if (index >= 0 && form.fields[index]) setExpanded(form.fields[index].key);
        }
        window.requestAnimationFrame(() => document.getElementById('builder-errors')?.focus());
    }
    async function persist() {
        const saved = await api.patch(`/admin/forms/${form.id}/`, formPayload(form));
        const next = editableForm(saved);
        setForm(next); setBaseline(JSON.stringify(formPayload(next)));
        return saved;
    }
    async function action(kind, copyData) {
        setBusy(kind); setError(null); setNotice(''); setDuplicateError(null);
        let saved = false;
        let copiedRequest = false;
        try {
            await persist(); saved = true;
            if (kind === 'publish') {
                const published = await api.post(`/admin/forms/${form.id}/publish/`);
                setForm(previous => ({ ...previous, status: 'published' }));
                setNotice(`Version ${published.version} published. Existing responses are preserved.`);
            } else if (kind === 'archive') {
                await api.patch(`/admin/forms/${form.id}/`, { status: 'archived' });
                setForm(previous => ({ ...previous, status: 'archived' }));
                setNotice('Form archived. Existing responses and versions are preserved.');
            } else if (kind === 'close') {
                await api.patch(`/admin/forms/${form.id}/`, { status: 'closed' });
                setForm(previous => ({ ...previous, status: 'closed' }));
                setNotice('Form closed. New responses are no longer accepted.');
            } else if (kind === 'duplicate') {
                copiedRequest = true;
                const copy = await api.post(`/admin/forms/${form.id}/duplicate/`, copyData);
                navigate(`/admin/forms/${copy.id}`);
            } else setNotice(form.status === 'published' ? 'Draft saved. Publish a new version to update the live form.' : 'Draft saved.');
            setConfirmation(null);
        } catch (failure) {
            if (kind === 'duplicate' && copiedRequest) setDuplicateError(failure);
            else { setDuplicate(false); setConfirmation(null); report(failure, saved); }
        } finally { setBusy(''); }
    }
    return <><PageHeader eyebrow="Registration form builder" title={form.title} description="Create a welcoming registration experience. Every change stays in your draft until you publish."><Link className="admin-button admin-button-secondary" to={`/admin/forms?event=${form.event}`}>← All forms</Link><Button variant="secondary" onClick={() => setPreview(true)} disabled={!!busy}>Preview</Button>{form.status === 'published' && form.event_slug && <Link className="admin-button admin-button-secondary" target="_blank" rel="noreferrer" to={`/events/${encodeURIComponent(form.event_slug)}/register/${encodeURIComponent(form.slug)}`}>Open published form ↗</Link>}</PageHeader>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3"><div className="flex flex-wrap items-center gap-3"><StatusBadge status={form.status} /><span className="text-xs text-slate-500">{form.status === 'published' ? 'Editing the next version' : 'Working draft'} · {form.fields.length}/100 questions</span></div><span role="status" className={`text-xs font-semibold ${dirty ? 'text-amber-700' : 'text-slate-500'}`}>{busy ? 'Working…' : dirty ? 'Unsaved changes' : 'All draft changes saved'}</span></div>
        <Notice>{notice}</Notice><ErrorNotice id="builder-errors" error={error} />
        <form noValidate onSubmit={event => { event.preventDefault(); action('save'); }} aria-busy={!!busy}>
            <fieldset disabled={!!busy} className="grid min-w-0 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
                <div className="min-w-0 space-y-5"><section className="admin-panel space-y-5 border-t-4 border-t-primary-700"><div><h2 className="text-lg text-primary-900">Form introduction</h2><p className="mt-1 text-xs text-slate-500">Tell applicants what they are signing up for.</p></div><Control label="Form title" required maxLength={255} value={form.title} error={errors.title} onChange={event => change('title', event.target.value)} /><Control label="Description" as="textarea" rows={4} value={form.description} error={errors.description} onChange={event => change('description', event.target.value)} placeholder="Welcome your applicants and explain what to expect." /></section>
                    <div className="flex items-center justify-between gap-3 px-1"><h2 className="text-sm font-semibold text-primary-900">Questions</h2><span className="text-xs text-slate-500">Use ↑ and ↓ to reorder</span></div>
                    {!form.fields.length && <EmptyState title="What would you like to know?" description="Add your first question. Start simple, then build a form that fits your event."><Button id="add-form-question" onClick={() => setPalette(true)}>＋ Add your first question</Button></EmptyState>}
                    {form.fields.map((field, index) => <FieldEditor key={field.key} field={field} index={index} total={form.fields.length} expanded={expanded === field.key} onExpand={() => setExpanded(expanded === field.key ? null : field.key)} onChange={value => fieldChange(field.key, value)} onMove={direction => move(index, direction)} onDelete={() => setConfirmation({ kind: 'delete', key: field.key, label: field.label || `Question ${index + 1}` })} errors={Array.isArray(errors.fields) ? errors.fields[index] : null} />)}
                    {!!form.fields.length && <button id="add-form-question" type="button" className="flex min-h-16 w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-primary-200 bg-primary-50/40 text-sm font-semibold text-primary-700 transition hover:border-primary-400 hover:bg-primary-50 disabled:opacity-50" disabled={form.fields.length >= 100} onClick={() => setPalette(true)}>＋ Add question</button>}
                    {errors.fields && !Array.isArray(errors.fields) && <p className="admin-field-error">{errorText(errors.fields)}</p>}
                </div>
                <aside className="min-w-0 space-y-5 xl:sticky xl:top-6"><section className="admin-panel space-y-5"><h2 className="text-base text-primary-900">Registration settings</h2><Control label="Opens (Asia/Dhaka)" type="datetime-local" value={form.opens_at} error={errors.opens_at} onChange={event => change('opens_at', event.target.value)} /><Control label="Closes (Asia/Dhaka)" type="datetime-local" value={form.closes_at} error={errors.closes_at} onChange={event => change('closes_at', event.target.value)} /><Control label="Capacity" type="number" min="1" step="1" value={form.capacity} error={errors.capacity} onChange={event => change('capacity', event.target.value)} placeholder="Unlimited" hint="Leave blank for no capacity limit." /><label className="flex items-start gap-3 text-xs leading-6"><input className="mt-1" type="checkbox" checked={form.allow_multiple_submissions} onChange={event => change('allow_multiple_submissions', event.target.checked)} />Allow multiple applications from the same applicant</label><Control label="Form type" maxLength={100} required value={form.form_type} error={errors.form_type} onChange={event => change('form_type', event.target.value)} /><Control label="Form slug" value={form.slug} readOnly error={errors.slug} hint="This form's stable link name." /></section>
                    <section className="rounded-2xl border border-accent-200 bg-accent-50 p-5"><h2 className="text-sm text-primary-900">Publish with confidence</h2><p className="mt-2 text-xs leading-6 text-slate-600">Preview your questions, then publish a new version. Earlier responses always keep their original questions.</p></section>
                </aside>
            </fieldset>
            <div className="sticky bottom-0 z-10 -mx-4 mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-white/95 px-4 py-4 backdrop-blur sm:-mx-8 sm:px-8 lg:-mx-10 lg:px-10"><div className="flex flex-wrap gap-2"><Button type="submit" variant="secondary" disabled={!!busy}>{busy === 'save' ? 'Saving…' : 'Save draft'}</Button><Button variant="ghost" disabled={!!busy} onClick={() => setDuplicate(true)}>Duplicate</Button>{form.status !== 'archived' && <Button variant="ghost" disabled={!!busy} onClick={() => setConfirmation({ kind: 'archive' })}>Archive form</Button>}{form.status === 'published' && <Button variant="ghost" disabled={!!busy} onClick={() => setConfirmation({ kind: 'close' })}>Close form</Button>}</div><Button disabled={!!busy || !form.fields.length} onClick={() => setConfirmation({ kind: 'publish' })}>{busy === 'publish' ? 'Publishing…' : form.status === 'published' ? 'Publish new version' : 'Publish form'}<span aria-hidden="true">↗</span></Button></div>
        </form>
        <p role="status" aria-live="polite" className="sr-only">{announcement}</p>
        {palette && <FieldPalette onClose={() => setPalette(false)} onAdd={add} />}
        {preview && <FormPreview form={form} onClose={() => setPreview(false)} />}
        {duplicate && <DuplicateDialog form={form} busy={!!busy} error={duplicateError} onClose={() => { setDuplicate(false); setDuplicateError(null); }} onDuplicate={data => action('duplicate', data)} />}
        {confirmation && <Dialog busy={!!busy} onClose={() => setConfirmation(null)} title={confirmation.kind === 'delete' ? 'Delete this question?' : confirmation.kind === 'archive' ? 'Archive this form?' : confirmation.kind === 'close' ? 'Close this form?' : 'Publish this form?'} description={confirmation.kind === 'delete' ? `“${confirmation.label}” will be removed from the draft. Published responses will not change.` : confirmation.kind === 'archive' ? 'Your draft will be saved and registration removed from public access. Existing responses, files and versions stay available to authorized reviewers.' : confirmation.kind === 'close' ? 'Your draft will be saved and new applications will no longer be accepted.' : 'Your draft will be saved as a new published version. It becomes available when the event is published and registration is open.'}><div className="flex flex-wrap justify-end gap-2"><Button variant="secondary" disabled={!!busy} onClick={() => setConfirmation(null)}>Cancel</Button><Button variant={confirmation.kind === 'delete' ? 'danger' : 'primary'} disabled={!!busy} onClick={() => {
            if (confirmation.kind === 'delete') {
                change('fields', form.fields.filter(field => field.key !== confirmation.key));
                setAnnouncement('Question deleted from the draft.'); setConfirmation(null); setError(null);
                window.requestAnimationFrame(() => document.getElementById('add-form-question')?.focus());
            } else action(confirmation.kind);
        }}>{busy ? 'Working…' : confirmation.kind === 'delete' ? 'Delete question' : confirmation.kind === 'archive' ? 'Save and archive' : confirmation.kind === 'close' ? 'Save and close' : 'Save and publish'}</Button></div></Dialog>}
    </>;
}
export default function FormBuilderPage() {
    const { id } = useParams();
    const resource = useResource(`/admin/forms/${id}/`);
    if (resource.loading) return <Loading label="Loading form builder…" />;
    if (resource.error) return <ErrorNotice error={resource.error} onRetry={resource.reload} />;
    return resource.data ? <FormBuilder key={id} initial={resource.data} /> : null;
}
