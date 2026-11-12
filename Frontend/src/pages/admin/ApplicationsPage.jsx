import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import useResource from '../../hooks/useResource';
import { downloadPrivate } from '../../services/api';
import { Button, Control, EmptyState, ErrorNotice, Loading, PageHeader, StatusBadge } from '../../components/admin/AdminUI';
import { APPLICATION_STATUSES, statusLabel, displayReviewDate } from '../../components/admin/reviewUtils';

export default function ApplicationsPage() {
    const [params, setParams] = useSearchParams();
    const query = new URLSearchParams(params);
    const [search, setSearch] = useState(params.get('search') || '');
    const [busy, setBusy] = useState('');
    const [error, setError] = useState(null);
    const events = useResource('/admin/events/', true);
    const forms = useResource('/admin/review/forms/', true);
    const submissions = useResource(`/admin/submissions/?${query}`);
    const page = Number(params.get('page') || 1);
    function filter(key, value) {
        const next = new URLSearchParams(params); next.delete('page');
        if (value) next.set(key, value); else next.delete(key);
        if (key === 'event') next.delete('registration_form');
        setParams(next);
    }
    async function exportFile(kind) {
        setBusy(kind); setError(null);
        const filters = new URLSearchParams(params); filters.delete('page'); filters.set('file_format', kind);
        try { await downloadPrivate(`/admin/submissions/export/?${filters}`, `munc-applications.${kind}`); }
        catch (failure) { setError(failure); } finally { setBusy(''); }
    }
    const failure = submissions.error || events.error || forms.error;
    return <><PageHeader title="Applications" description="Review applications for your assigned events. Answers, documents and notes remain private."><Button variant="secondary" disabled={!!busy || submissions.loading || !!failure} onClick={() => exportFile('csv')}>{busy === 'csv' ? 'Exporting…' : 'Export CSV'}</Button><Button variant="secondary" disabled={!!busy || submissions.loading || !!failure} onClick={() => exportFile('xlsx')}>{busy === 'xlsx' ? 'Exporting…' : 'Export XLSX'}</Button></PageHeader>
        <ErrorNotice error={error} /><ErrorNotice error={failure} onRetry={() => { submissions.reload(); events.reload(); forms.reload(); }} />
        <div className="admin-panel mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4"><form onSubmit={event => { event.preventDefault(); filter('search', search.trim()); }} className="flex items-end gap-2 md:col-span-2"><Control className="flex-1" label="Search applications" type="search" maxLength={200} placeholder="Name, email or reference" value={search} onChange={event => setSearch(event.target.value)} /><Button type="submit">Search</Button></form><Control label="Event" as="select" value={params.get('event') || ''} onChange={event => filter('event', event.target.value)}><option value="">All assigned events</option>{events.data?.map(event => <option key={event.id} value={event.id}>{event.title}</option>)}</Control><Control label="Registration form" as="select" value={params.get('registration_form') || ''} onChange={event => filter('registration_form', event.target.value)}><option value="">All forms</option>{forms.data?.filter(form => !params.get('event') || String(form.event) === params.get('event')).map(form => <option key={form.id} value={form.id}>{form.title}</option>)}</Control><Control label="Application status" as="select" value={params.get('status') || ''} onChange={event => filter('status', event.target.value)}><option value="">All statuses</option>{APPLICATION_STATUSES.map(status => <option key={status} value={status}>{statusLabel(status)}</option>)}</Control><Control label="Order applications" as="select" value={params.get('ordering') || '-submitted_at'} onChange={event => filter('ordering', event.target.value)}><option value="-submitted_at">Newest first</option><option value="submitted_at">Oldest first</option><option value="reference_number">Reference</option><option value="status">Status</option></Control></div>
        {submissions.loading ? <Loading label="Loading applications…" /> : !failure && (submissions.data?.results?.length ? <><p role="status" className="mb-3 text-sm text-slate-500">{submissions.data.count} applications · page {page}</p><div role="region" aria-label="Applications table" tabIndex={0} className="overflow-x-auto rounded-2xl border border-slate-200 bg-white"><table className="w-full min-w-[650px] text-left text-sm"><thead className="bg-slate-50 text-xs text-slate-600"><tr>{['Reference', 'Event / form', 'Status', 'Submitted'].map(label => <th key={label} scope="col" className="p-4">{label}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{submissions.data.results.map(item => <tr key={item.id}><td className="p-4"><Link className="break-all font-mono font-semibold text-primary-700 underline underline-offset-4" to={`/admin/submissions/${item.id}`}>{item.reference_number}</Link></td><td className="p-4"><p className="font-medium text-primary-900">{item.event_title}</p><p className="mt-1 text-xs text-slate-500">{item.form_title}</p></td><td className="p-4"><StatusBadge status={item.status} /></td><td className="p-4 whitespace-nowrap">{displayReviewDate(item.submitted_at)}</td></tr>)}</tbody></table></div><nav aria-label="Application pages" className="mt-5 flex items-center justify-between gap-3"><Button variant="secondary" disabled={!submissions.data.previous} onClick={() => { query.set('page', page - 1); setParams(query); }}>Previous</Button><span className="text-sm text-slate-500">Page {page}</span><Button variant="secondary" disabled={!submissions.data.next} onClick={() => { query.set('page', page + 1); setParams(query); }}>Next</Button></nav></> : <EmptyState title="No applications found" description="Try changing the event, form, search or status filters. New applications will appear here after submission." />)}
    </>;
}
