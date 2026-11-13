import { useContext, useState } from 'react';
import useResource from '../../hooks/useResource';
import { AdminContext } from '../../contexts/AdminContext';
import { api } from '../../services/api';
import { Button, Control, ErrorNotice, Loading, Notice, StatusBadge } from './AdminUI';
import { displayReviewDate } from './reviewUtils';

function PaymentEditor({ payment, id, reload }) {
    const [form, setForm] = useState({ ...payment, next_instructions: '' });
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    return <form className="mt-5 space-y-4" onSubmit={async event => {
        event.preventDefault();
        if (form.status === 'verified' && !window.confirm('Confirm that you independently verified payment. A screenshot or transaction ID alone is not verification.')) return;
        setBusy(true); setError(null);
        try { await api.patch(`/admin/email/payments/${id}/`, { status: form.status, amount: form.amount === '' ? null : form.amount, currency: form.currency, next_instructions: form.next_instructions }); reload(); }
        catch (failure) { setError(failure); } finally { setBusy(false); }
    }}><ErrorNotice error={error} /><fieldset disabled={busy} className="space-y-4"><Control label="Payment status" as="select" value={form.status} onChange={event => setForm({ ...form, status: event.target.value })}>{['unpaid', 'pending', 'verified', 'rejected'].map(status => <option key={status} value={status}>{status}</option>)}</Control><div className="grid gap-4 sm:grid-cols-2"><Control label="Verified amount (optional)" type="number" min="0" step="0.01" value={form.amount} onChange={event => setForm({ ...form, amount: event.target.value })} /><Control label="Payment currency" maxLength={3} value={form.currency} onChange={event => setForm({ ...form, currency: event.target.value.toUpperCase() })} /></div><Control label="Payment next instructions" as="textarea" rows={3} value={form.next_instructions} onChange={event => setForm({ ...form, next_instructions: event.target.value })} /></fieldset><Button type="submit" disabled={busy}>Save payment decision</Button></form>;
}
export default function SubmissionEmailPanel({ id, revision }) {
    const canManage = useContext(AdminContext)?.canManage;
    const resource = useResource(`/admin/email/submissions/${id}/?revision=${encodeURIComponent(revision || '')}`);
    return <section className="admin-panel mt-6"><h2 className="text-lg text-primary-900">Payment and email notifications</h2><p className="mt-3 text-sm leading-7 text-slate-500">Payment verification is separate from application selection. Uploaded payment evidence never verifies a payment automatically.</p><ErrorNotice error={resource.error} onRetry={resource.reload} />{resource.loading ? <Loading /> : resource.data && <><div className="mt-4"><StatusBadge status={resource.data.payment?.status || 'unpaid'} /></div>{canManage && <PaymentEditor key={JSON.stringify(resource.data.payment)} payment={resource.data.payment || { status: 'unpaid', amount: '', currency: 'BDT' }} id={id} reload={resource.reload} />}<h3 className="mt-7 text-sm font-semibold text-primary-900">Recent email delivery</h3>{resource.data.messages?.length ? <ul className="mt-3 space-y-3">{resource.data.messages.map(message => <li key={message.id} className="flex flex-wrap justify-between gap-2 rounded-lg bg-slate-50 p-3 text-xs"><span>{message.message_type.replaceAll('_', ' ')}<span className="mt-1 block text-slate-500">{displayReviewDate(message.created_at)}</span></span><StatusBadge status={message.status} /></li>)}</ul> : <Notice>No email notifications recorded for this application.</Notice>}</>}</section>;
}
