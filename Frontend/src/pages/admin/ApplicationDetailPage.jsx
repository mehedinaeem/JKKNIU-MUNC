import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import useResource from '../../hooks/useResource';
import useUnsavedChanges from '../../hooks/useUnsavedChanges';
import { api, downloadPrivate } from '../../services/api';
import { Button, Control, ErrorNotice, Loading, Notice, PageHeader, StatusBadge } from '../../components/admin/AdminUI';
import { answerLabel, APPLICATION_STATUSES, statusLabel, displayReviewDate } from '../../components/admin/reviewUtils';

function ApplicationReview({ initial }) {
    const [data, setData] = useState(initial);
    const [status, setStatus] = useState(initial.status);
    const [note, setNote] = useState('');
    const [busy, setBusy] = useState('');
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState('');
    useUnsavedChanges(!!note.trim() || status !== data.status);
    async function save(kind) {
        setBusy(kind); setError(null); setNotice('');
        let committed = false;
        try {
            if (kind === 'status') await api.patch(`/admin/submissions/${data.id}/status/`, { status });
            else await api.post(`/admin/submissions/${data.id}/notes/`, { body: note });
            committed = true;
            if (kind === 'note') setNote('');
            const refreshed = await api.get(`/admin/submissions/${data.id}/`);
            setData(refreshed);
            setNotice(kind === 'status' ? 'Application status updated.' : 'Private reviewer note added.');
        } catch (failure) {
            setError(failure);
            if (committed) setNotice('Your change was saved, but the refreshed history could not load. Reload this page before making another change.');
        } finally { setBusy(''); }
    }
    async function download(file) {
        setBusy(`file-${file.id}`); setError(null);
        try { await downloadPrivate(`/submission-files/${file.id}/`, `application-${data.reference_number}-${file.id}.${file.content_type === 'application/pdf' ? 'pdf' : file.content_type === 'image/png' ? 'png' : 'jpg'}`); }
        catch (failure) { setError(failure); } finally { setBusy(''); }
    }
    const timeline = [...(data.history || []).map(item => ({ ...item, kind: 'status' })), ...(data.reviewer_notes || []).map(item => ({ ...item, kind: 'note' }))].sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id);
    return <><PageHeader title="Application review" description={`${data.event_title} · ${data.form_title}`}><Link className="admin-button admin-button-secondary" to={`/admin/submissions?event=${data.event}`}>← Applications</Link></PageHeader><ErrorNotice error={error} /><Notice>{notice}</Notice><div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5"><div className="min-w-0"><p className="break-all font-mono text-sm font-semibold text-primary-800">{data.reference_number}</p><p className="mt-2 break-all text-sm text-slate-600">{data.applicant_email || 'No historical email recorded'}</p><p className="mt-2 text-xs text-slate-500">Submitted {displayReviewDate(data.submitted_at)}</p></div><StatusBadge status={data.status} /></div>
        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]"><section className="admin-panel min-w-0"><h2 className="text-lg text-primary-900">Submitted answers</h2><p className="mt-2 text-xs leading-6 text-slate-500">Questions and option labels come from the version submitted by this applicant.</p><dl className="mt-5 divide-y divide-slate-100">{data.form_schema.fields.map(field => <div key={field.key} className="py-5"><dt className="text-sm font-semibold text-primary-900">{field.label}</dt><dd className="mt-3 whitespace-pre-wrap break-words text-sm leading-7 text-slate-600">{field.field_type === 'file' ? (() => { const file = data.files.find(file => file.field_key === field.key); return file ? <div><p className="break-all">{file.original_filename} · {(file.file_size / 1024).toFixed(1)} KiB</p><Button className="mt-3" variant="secondary" disabled={!!busy} onClick={() => download(file)}>{busy === `file-${file.id}` ? 'Downloading…' : 'Download private file'}</Button></div> : 'No file submitted'; })() : answerLabel(field, data.answers[field.key])}</dd></div>)}</dl></section>
        <div className="min-w-0 space-y-6"><section className="admin-panel"><h2 className="mb-4 text-lg text-primary-900">Review decision</h2><form onSubmit={event => { event.preventDefault(); save('status'); }} className="space-y-4"><Control label="Review status" as="select" disabled={!!busy} value={status} error={error?.errors?.status} onChange={event => setStatus(event.target.value)}>{APPLICATION_STATUSES.map(value => <option key={value} value={value}>{statusLabel(value)}</option>)}</Control><Button type="submit" disabled={!!busy || status === data.status}>{busy === 'status' ? 'Saving…' : 'Update status'}</Button></form></section><section className="admin-panel"><h2 className="mb-4 text-lg text-primary-900">Private reviewer note</h2><form onSubmit={event => { event.preventDefault(); save('note'); }} className="space-y-4"><Control label="Note" as="textarea" rows={5} required maxLength={10000} value={note} disabled={!!busy} error={error?.errors?.body} onChange={event => setNote(event.target.value)} hint="Visible only to administrators assigned to this event. Notes are retained in the review history." /><Button type="submit" disabled={!!busy || !note.trim()}>{busy === 'note' ? 'Adding…' : 'Add private note'}</Button></form></section><section className="admin-panel"><h2 className="text-lg text-primary-900">Review history</h2><p className="mt-2 text-xs text-slate-500">Newest activity first.</p><ol className="mt-5 space-y-5">{timeline.map(item => <li key={`${item.kind}-${item.id}`} className="border-l-2 border-primary-100 pl-4"><p className="text-xs font-semibold text-primary-800">{item.kind === 'note' ? item.author_name : item.actor} · {displayReviewDate(item.created_at)}</p><p className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-slate-600">{item.kind === 'note' ? item.body : `${statusLabel(item.previous_status)} → ${statusLabel(item.status)}`}</p></li>)}<li className="border-l-2 border-slate-200 pl-4 text-xs text-slate-500">Application submitted · {displayReviewDate(data.submitted_at)}</li></ol></section></div></div>
    </>;
}
export default function ApplicationDetailPage() {
    const { id } = useParams();
    const resource = useResource(`/admin/submissions/${id}/`);
    if (resource.loading) return <Loading label="Loading private application…" />;
    if (resource.error) return <ErrorNotice error={resource.error} onRetry={resource.reload} />;
    return resource.data ? <ApplicationReview key={id} initial={resource.data} /> : null;
}
