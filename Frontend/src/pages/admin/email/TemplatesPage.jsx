import { useCallback, useEffect, useRef, useState } from 'react';
import useResource from '../../../hooks/useResource';
import useAdminAuth from '../../../hooks/useAdminAuth';
import useUnsavedChanges from '../../../hooks/useUnsavedChanges';
import { api } from '../../../services/api';
import { Button, Control, ErrorNotice, Loading, Notice, PageHeader } from '../../../components/admin/AdminUI';
import { RichEmailEditor } from './EmailUI';
import useEmailPreview from './useEmailPreview';

function TemplateEditor({ initial, events, onSaved, isSuper, newCopy, registerGuard }) {
    const [form, setForm] = useState({ ...initial, event: initial.event || '' });
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState('');
    const [baseline, setBaseline] = useState(JSON.stringify(form));
    const preview = useEmailPreview();
    const readOnly = !isSuper && !form.event && !newCopy;
    const dirty = !readOnly && JSON.stringify(form) !== baseline;
    useUnsavedChanges(dirty);
    useEffect(() => registerGuard(dirty ? () => window.confirm('Discard unsaved template changes?') : null), [dirty, registerGuard]);
    async function save(event) {
        event.preventDefault(); setBusy(true); setError(null);
        try {
            const payload = { ...form, event: form.event ? Number(form.event) : null };
            const saved = initial.id && !newCopy ? await api.patch(`/admin/email/templates/${initial.id}/`, payload) : await api.post('/admin/email/templates/', payload);
            setBaseline(JSON.stringify(form)); setNotice('Template saved. Existing queued messages keep their saved content.'); onSaved(saved);
        } catch (failure) { setError(failure); } finally { setBusy(false); }
    }
    return <form className="admin-panel space-y-5" onSubmit={save}><ErrorNotice error={error} /><Notice>{notice}</Notice>{preview.output}<fieldset disabled={busy || readOnly} className="space-y-5"><Control label="Template name" required value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} /><Control label="Template key" required value={form.template_key} onChange={event => setForm({ ...form, template_key: event.target.value })} hint="Use the built-in notification key to customize an automatic email, or a custom key for campaigns." /><Control label="Template event" as="select" value={form.event} disabled={busy || readOnly || (!!initial.id && !newCopy)} onChange={event => setForm({ ...form, event: event.target.value })}><option value="">{isSuper ? 'Global default' : 'Choose assigned event'}</option>{events.map(event => <option key={event.id} value={event.id}>{event.title}</option>)}</Control><Control label="Template subject" required value={form.subject} onChange={event => setForm({ ...form, subject: event.target.value })} maxLength={255} /><RichEmailEditor value={form.html_content} disabled={busy || readOnly} onChange={value => setForm({ ...form, html_content: value })} /><Control label="Template plain text" required as="textarea" rows={8} value={form.text_content} onChange={event => setForm({ ...form, text_content: event.target.value })} /><label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" checked={form.is_active} onChange={event => setForm({ ...form, is_active: event.target.checked })} />Active template</label></fieldset><div className="flex flex-wrap gap-3">{!readOnly && <Button type="submit" disabled={busy || (!isSuper && !form.event)}>Save template</Button>}<Button variant="secondary" disabled={busy} onClick={() => preview.show(form)}>Preview example</Button></div>{readOnly && <p className="text-sm text-slate-500">This global default is read-only for Event Admins. Use Customize for event to create your own override.</p>}</form>;
}
export default function TemplatesPage() {
    const resource = useResource('/admin/email/templates/', true);
    const events = useResource('/admin/events/', true);
    const { isSuper } = useAdminAuth();
    const [selected, setSelected] = useState(null);
    const [copy, setCopy] = useState(false);
    const [generation, setGeneration] = useState(0);
    const [notice, setNotice] = useState('');
    const guard = useRef(null);
    const registerGuard = useCallback(value => { guard.current = value; return () => { if (guard.current === value) guard.current = null; }; }, []);
    return <><PageHeader title="Email templates" description="Approved variables and sanitized formatting; no code or Django template execution."><Button onClick={() => { if (guard.current && !guard.current()) return; setSelected({ name: '', template_key: 'custom_announcement', event: '', subject: 'Event Update — {{event_name}}', html_content: '<p>Hello {{full_name}},</p>', text_content: 'Hello {{full_name}},', is_active: true }); setCopy(true); setGeneration(value => value + 1); }}>New template</Button></PageHeader><Notice>{notice}</Notice><ErrorNotice error={resource.error || events.error} onRetry={resource.reload} />{resource.loading || events.loading ? <Loading /> : <div className="grid items-start gap-6 xl:grid-cols-[280px_minmax(0,1fr)]"><div className="admin-panel space-y-3">{resource.data?.map(template => <div key={template.id}><button type="button" className="w-full rounded-lg p-3 text-left text-sm font-semibold text-primary-800 hover:bg-primary-50" onClick={() => { if (!guard.current || guard.current()) { setSelected(template); setCopy(false); setGeneration(value => value + 1); } }}>{template.name}<span className="mt-1 block text-xs font-normal text-slate-500">{template.event_title || 'Global default'} · {template.is_active ? 'Active' : 'Inactive'}</span></button>{!template.event && <Button variant="secondary" className="mb-3" onClick={() => { if (guard.current && !guard.current()) return; setSelected({ ...template, id: undefined, event: '' }); setCopy(true); setGeneration(value => value + 1); }}>Customize for event</Button>}</div>)}</div>{selected ? <TemplateEditor key={generation} initial={selected} events={events.data || []} newCopy={copy} isSuper={isSuper} registerGuard={registerGuard} onSaved={saved => { setSelected(saved); setCopy(false); setGeneration(value => value + 1); setNotice('Template saved. Existing queued messages retain their original content.'); resource.reload(); }} /> : <p className="admin-panel text-sm text-slate-500">Choose a template to edit or preview.</p>}</div>}</>;
}
