import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../../../services/api';
import useResource from '../../../hooks/useResource';
import useUnsavedChanges from '../../../hooks/useUnsavedChanges';
import { Button, Control, Dialog, ErrorNotice, Loading, Notice, PageHeader, StatusBadge } from '../../../components/admin/AdminUI';
import { toApiDate } from '../../../components/admin/adminUtils';
import { EmailPreview, RichEmailEditor } from './EmailUI';

const blank = { name: '', event: '', subject: '', template: '', html_content: '<p>Hello {{full_name}},</p><p>{{next_instructions}}</p>', text_content: 'Hello {{full_name}},\n\n{{next_instructions}}', classification: 'operational', recipient_filter: {} };
function Editor({ initial }) {
    const navigate = useNavigate();
    const events = useResource('/admin/events/', true);
    const configuration = useResource('/admin/email/configuration/');
    const templates = useResource('/admin/email/templates/', true);
    const [form, setForm] = useState(initial || blank);
    const [baseline, setBaseline] = useState(JSON.stringify(initial || blank));
    const [busy, setBusy] = useState('');
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState('');
    const [preview, setPreview] = useState(null);
    const [confirmation, setConfirmation] = useState(null);
    const [scheduled, setScheduled] = useState('');
    const [recipientSearch, setRecipientSearch] = useState('');
    const [count, setCount] = useState({ key: '', count: null, error: null });
    const [editorGeneration, setEditorGeneration] = useState(0);
    const testKey = useRef(crypto.randomUUID());
    const frozen = !!form.snapshot_at || !['draft', 'failed', undefined].includes(form.status);
    const forms = useResource(form.event ? `/admin/review/forms/` : null, true);
    const options = useResource(form.event && form.recipient_filter.selection === 'custom' ? `/admin/email/recipient-options/?event=${form.event}&search=${encodeURIComponent(recipientSearch)}` : null);
    const countKey = JSON.stringify([form.event, form.classification, form.recipient_filter]);
    useUnsavedChanges(!frozen && JSON.stringify(form) !== baseline);
    useEffect(() => {
        if (!form.event || frozen) return;
        let active = true;
        const timer = window.setTimeout(() => {
            api.post('/admin/email/recipients/', { event: Number(form.event), classification: form.classification, recipient_filter: form.recipient_filter })
                .then(data => { if (active) setCount({ key: countKey, count: data.count, error: null }); })
                .catch(error => { if (active) setCount({ key: countKey, count: null, error }); });
        }, 500);
        return () => { active = false; window.clearTimeout(timer); };
    }, [countKey, frozen, form.event, form.classification, form.recipient_filter]);
    function change(key, value) { setForm(previous => ({ ...previous, [key]: value })); setNotice(''); }
    function group(value) {
        const next = { form_ids: form.recipient_filter.form_ids || [], form_types: form.recipient_filter.form_types || [] };
        if (['approved', 'shortlisted', 'rejected'].includes(value)) next.statuses = [value];
        if (['unpaid', 'verified'].includes(value)) next.payment_status = value;
        if (value === 'custom') { next.selection = 'custom'; next.submission_ids = []; }
        change('recipient_filter', next);
    }
    async function save() {
        const payload = Object.fromEntries(Object.keys(blank).map(key => [key, form[key]]));
        payload.event = Number(form.event); payload.template = form.template ? Number(form.template) : null;
        const saved = form.id ? await api.patch(`/admin/email/campaigns/${form.id}/`, payload) : await api.post('/admin/email/campaigns/', payload);
        setForm(saved); setBaseline(JSON.stringify(saved));
        if (!form.id) navigate(`/admin/email/campaigns/${saved.id}`, { replace: true });
        return saved;
    }
    async function action(kind) {
        setBusy(kind); setError(null); setNotice('');
        try {
            const saved = frozen ? form : await save();
            if (kind === 'save') setNotice('Campaign draft saved.');
            else {
                const result = await api.post(`/admin/email/campaigns/${saved.id}/${kind}/`, { confirm: true, scheduled_at: toApiDate(scheduled), request_key: testKey.current });
                if (kind === 'preview') setPreview(result);
                else if (kind === 'test') { setNotice('Test email queued for your administrator email. The queue worker must run; this is not a delivery confirmation.'); testKey.current = crypto.randomUUID(); }
                else { setForm(result); setBaseline(JSON.stringify(result)); setNotice('Campaign action saved. Background processing handles messages; no delivery is assumed.'); }
            }
            setConfirmation(null);
        } catch (failure) { setError(failure); } finally { setBusy(''); }
    }
    const eligible = count.key === countKey ? count.count : null;
    const selectedGroup = form.recipient_filter.selection === 'custom' ? 'custom' : form.recipient_filter.payment_status || form.recipient_filter.statuses?.[0] || 'all';
    return <><PageHeader title={form.id ? form.name : 'New email campaign'} description="Recipients are deduplicated and frozen by the worker when sending begins. Each message goes to one applicant only.">{form.status && <StatusBadge status={form.status} />}</PageHeader><ErrorNotice error={error || events.error || templates.error} /><Notice>{notice}</Notice><Notice>{configuration.data?.enabled === false ? 'Email transport is disabled. Drafts, previews and queued jobs are retained; nothing sends until the server configuration and queue worker are enabled.' : configuration.data?.configured === false ? 'The email provider is not configured yet. Queued jobs will wait for operator setup.' : ''}</Notice><form onSubmit={event => { event.preventDefault(); action('save'); }} className="space-y-6"><fieldset disabled={!!busy || frozen} className="admin-panel grid min-w-0 gap-5 sm:grid-cols-2"><Control label="Campaign name" required maxLength={255} value={form.name} onChange={event => change('name', event.target.value)} /><Control label="Event" as="select" required disabled={!!form.id || !!busy || frozen} value={form.event} onChange={event => { setForm({ ...blank, name: form.name, event: event.target.value }); setEditorGeneration(value => value + 1); }}><option value="">Choose event</option>{events.data?.map(event => <option key={event.id} value={event.id}>{event.title}</option>)}</Control><Control label="Message classification" as="select" value={form.classification} onChange={event => change('classification', event.target.value)} hint="Operational messages must be legitimate updates for this event. Optional promotion requires recorded consent and an unsubscribe link."><option value="operational">Operational event update</option><option value="marketing">Optional marketing announcement</option></Control><Control label="Recipient group" as="select" value={selectedGroup} onChange={event => group(event.target.value)}><option value="all">All registered applicants</option><option value="approved">Approved applicants</option><option value="shortlisted">Shortlisted applicants</option><option value="rejected">Rejected applicants</option><option value="unpaid">Payment not verified</option><option value="verified">Payment verified</option><option value="custom">Custom selected applicants</option></Control><Control label="Form type group" as="select" value={form.recipient_filter.form_types?.[0] || ''} onChange={event => change('recipient_filter', { ...form.recipient_filter, form_ids: [], form_types: event.target.value ? [event.target.value] : [] })} hint="Choose a Delegate, Executive Board or custom form type across this event."><option value="">All form types</option>{[...new Set((forms.data || []).filter(item => String(item.event) === String(form.event)).map(item => item.form_type))].map(type => <option key={type} value={type}>{type.replaceAll('_', ' ').replaceAll('-', ' ')}</option>)}</Control><Control label="Registration category" as="select" value={form.recipient_filter.form_ids?.[0] || ''} onChange={event => change('recipient_filter', { ...form.recipient_filter, form_ids: event.target.value ? [Number(event.target.value)] : [] })} hint="Select a Delegate, Executive Board or any custom form; types are read from your event."><option value="">All forms for this event</option>{forms.data?.filter(item => String(item.event) === String(form.event) && (!form.recipient_filter.form_types?.length || form.recipient_filter.form_types.includes(item.form_type))).map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</Control><Control label="Email template" as="select" value={form.template || ''} onChange={event => { const template = templates.data.find(item => String(item.id) === event.target.value); if (template) { setForm({ ...form, template: template.id, subject: template.subject, html_content: template.html_content, text_content: template.text_content }); setEditorGeneration(value => value + 1); } else change('template', ''); }}><option value="">Custom content</option>{templates.data?.filter(item => item.is_active && (!item.event || String(item.event) === String(form.event))).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Control>
        {form.recipient_filter.selection === 'custom' && <div className="space-y-3 sm:col-span-2"><Control label="Find applicants" type="search" value={recipientSearch} onChange={event => setRecipientSearch(event.target.value)} placeholder="Name, email or reference" /><ErrorNotice error={options.error} /><p className="text-xs text-slate-500">{form.recipient_filter.submission_ids?.length || 0} selected. Search shows one page at a time; selections remain selected across searches.</p>{options.data?.results?.map(row => <label key={row.id} className="flex min-h-11 items-start gap-3 text-sm"><input type="checkbox" className="mt-1" checked={form.recipient_filter.submission_ids?.includes(row.id) || false} onChange={event => change('recipient_filter', { ...form.recipient_filter, submission_ids: event.target.checked ? [...(form.recipient_filter.submission_ids || []), row.id] : form.recipient_filter.submission_ids.filter(id => id !== row.id) })} /><span className="min-w-0 break-all">{row.full_name} · {row.applicant_email}<span className="mt-1 block text-xs text-slate-500">{row.reference_number}</span></span></label>)}</div>}
        <div className="sm:col-span-2"><ErrorNotice error={count.key === countKey ? count.error : null} /><p role="status" className="rounded-lg bg-primary-50 p-4 text-sm font-semibold text-primary-800">{frozen ? 'Campaign settings are locked. Recipients are frozen when sending begins; see progress below.' : eligible == null ? 'Choose recipients to calculate eligibility.' : `${eligible} unique eligible recipients`}</p></div></fieldset><fieldset disabled={!!busy || frozen} className="admin-panel space-y-5"><Control label="Email subject" required maxLength={255} value={form.subject} onChange={event => change('subject', event.target.value)} /><RichEmailEditor key={editorGeneration} value={form.html_content} disabled={!!busy || frozen} onChange={value => change('html_content', value)} /><Control label="Plain-text fallback" as="textarea" rows={7} required value={form.text_content} onChange={event => change('text_content', event.target.value)} maxLength={100000} /></fieldset><div className="flex flex-wrap gap-3">{!frozen && <Button type="submit" disabled={!!busy || !form.event}>Save draft</Button>}<Button variant="secondary" disabled={!!busy || !form.event} onClick={() => action('preview')}>Preview</Button><Button variant="secondary" disabled={!!busy || !form.event} onClick={() => action('test')}>Send test to my admin email</Button>{(form.status === 'draft' || !form.id) && <><Button disabled={!!busy || !eligible} onClick={() => setConfirmation('send')}>Send now…</Button><Button variant="secondary" disabled={!!busy || !eligible} onClick={() => setConfirmation('schedule')}>Schedule…</Button></>}{['ready', 'scheduled', 'sending'].includes(form.status) && <Button variant="secondary" disabled={!!busy} onClick={() => action('pause')}>Pause unsent messages</Button>}{form.status === 'paused' && <Button disabled={!!busy} onClick={() => action('resume')}>Resume</Button>}{form.id && !['completed', 'cancelled'].includes(form.status) && <Button variant="danger" disabled={!!busy} onClick={() => setConfirmation('cancel')}>Cancel unsent messages…</Button>}</div></form>{form.progress && <section className="admin-panel mt-6"><h2 className="text-lg text-primary-900">Sending progress</h2><p className="mt-3 text-sm leading-7">{Object.entries(form.progress).map(([key, value]) => `${key}: ${value}`).join(' · ') || 'No recipient snapshot yet.'}</p><p className="mt-2 text-xs text-slate-500">Pausing or cancellation stops unclaimed jobs; an already claimed provider request may finish.</p><Button variant="secondary" className="mt-4" disabled={!!busy} onClick={async () => { try { const current = await api.get(`/admin/email/campaigns/${form.id}/`); setForm(current); setBaseline(JSON.stringify(current)); } catch (failure) { setError(failure); } }}>Refresh progress</Button></section>}{preview && <EmailPreview data={preview} onClose={() => setPreview(null)} />}{confirmation && <Dialog title={confirmation === 'cancel' ? 'Cancel remaining messages?' : confirmation === 'schedule' ? 'Schedule this campaign?' : 'Queue this campaign now?'} description={confirmation === 'cancel' ? 'Already accepted messages cannot be recalled. Only unsent jobs are stopped.' : `${eligible ?? 'Selected'} unique recipients currently qualify. Operational messages must be legitimate event updates; optional marketing requires explicit consent.`} busy={!!busy} onClose={() => setConfirmation(null)}><ErrorNotice error={error} />{confirmation === 'schedule' && <Control label="Scheduled time (Asia/Dhaka)" type="datetime-local" value={scheduled} onChange={event => setScheduled(event.target.value)} />}<div className="mt-5 flex justify-end gap-3"><Button variant="secondary" disabled={!!busy} onClick={() => setConfirmation(null)}>Back</Button><Button disabled={!!busy || (confirmation === 'schedule' && !scheduled)} onClick={() => action(confirmation)}>{busy ? 'Saving…' : 'Confirm'}</Button></div></Dialog>}</>;
}
export default function CampaignEditorPage() {
    const { id } = useParams();
    const resource = useResource(id ? `/admin/email/campaigns/${id}/` : null);
    if (resource.loading) return <Loading />;
    if (resource.error) return <ErrorNotice error={resource.error} onRetry={resource.reload} />;
    return <Editor key={id || 'new'} initial={resource.data} />;
}
