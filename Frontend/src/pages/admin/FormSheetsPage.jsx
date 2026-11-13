import { useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import useResource from '../../hooks/useResource';
import { downloadPrivate } from '../../services/api';
import { Button, Control, Dialog, EmptyState, ErrorNotice, Loading, PageHeader, StatusBadge } from '../../components/admin/AdminUI';
import PrivateImage from '../../components/admin/PrivateImage';
import { answerLabel, APPLICATION_STATUSES, displayReviewDate, statusLabel } from '../../components/admin/reviewUtils';

function ResponseSheet({ formId }) {
    const [params, setParams] = useSearchParams();
    const [search, setSearch] = useState(params.get('search') || '');
    const [busy, setBusy] = useState('');
    const [error, setError] = useState(null);
    const [image, setImage] = useState(null);
    const resource = useResource(`/admin/forms/${encodeURIComponent(formId)}/sheet/?${params}`);
    const data = resource.data;
    function filter(key, value) {
        const next = new URLSearchParams(params); next.delete('page');
        if (value) next.set(key, value); else next.delete(key);
        setParams(next);
    }
    async function download(path, filename, kind) {
        setBusy(kind); setError(null);
        try { await downloadPrivate(path, filename); }
        catch (failure) { setError(failure); } finally { setBusy(''); }
    }
    function exportFile(kind) {
        const query = new URLSearchParams(params); query.delete('page'); query.set('registration_form', formId); query.set('file_format', kind);
        download(`/admin/submissions/export/?${query}`, `${data.form.slug}-responses.${kind}`, kind);
    }
    function fileCell(row, field) {
        const file = row.files.find(file => file.field_key === field.key);
        if (!file) return <span className="text-slate-400">No file</span>;
        const isImage = ['image/png', 'image/jpeg'].includes(file.content_type);
        return <div className="space-y-2">{isImage && <><PrivateImage key={file.id} file={file} /><button type="button" className="block min-h-9 text-xs font-semibold text-primary-700 underline underline-offset-4" onClick={() => setImage(file)}>Enlarge image</button></>}<p className="max-w-48 break-all text-xs text-slate-500">{file.original_filename || 'Attachment'}</p><button type="button" disabled={!!busy} className="min-h-9 text-xs font-semibold text-primary-700 underline underline-offset-4 disabled:opacity-50" onClick={() => download(`/submission-files/${file.id}/`, `application-${row.reference_number}-${file.id}.${file.content_type === 'application/pdf' ? 'pdf' : file.content_type === 'image/png' ? 'png' : 'jpg'}`, `file-${file.id}`)}>{busy === `file-${file.id}` ? 'Downloading…' : 'Download file'}</button></div>;
    }
    return <><ErrorNotice error={error} /><ErrorNotice error={resource.error} onRetry={resource.reload} />
        <div className="admin-panel mb-5 flex flex-wrap items-end gap-4"><form className="flex min-w-0 flex-1 basis-64 items-end gap-2" onSubmit={event => { event.preventDefault(); filter('search', search.trim()); }}><Control className="min-w-0 flex-1" label="Search sheet" type="search" placeholder="Name, email or reference" maxLength={200} value={search} onChange={event => setSearch(event.target.value)} /><Button type="submit">Search</Button></form><Control label="Sheet status filter" as="select" value={params.get('status') || ''} onChange={event => filter('status', event.target.value)}><option value="">All statuses</option>{APPLICATION_STATUSES.map(status => <option key={status} value={status}>{statusLabel(status)}</option>)}</Control><Control label="Sheet order" as="select" value={params.get('ordering') || '-submitted_at'} onChange={event => filter('ordering', event.target.value)}><option value="-submitted_at">Newest first</option><option value="submitted_at">Oldest first</option><option value="reference_number">Reference</option></Control><Button variant="secondary" disabled={resource.loading} onClick={resource.reload}>Refresh</Button></div>
        {resource.loading ? <Loading label="Loading form responses…" /> : data && <><section className="overflow-hidden rounded-2xl border border-slate-200 bg-white" aria-labelledby="response-sheet-title"><div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 bg-primary-50/50 p-5"><div className="min-w-0"><h2 id="response-sheet-title" className="break-words text-xl font-bold text-primary-900">{data.form.title}</h2><p className="mt-2 text-sm text-slate-500">{data.form.event_title}</p><p role="status" className="mt-3 text-xs text-slate-600">{data.count} responses · {data.columns.length} question columns · page {data.page_number} of {data.total_pages}</p></div><div className="flex flex-wrap gap-2"><Button variant="secondary" disabled={!!busy} onClick={() => exportFile('csv')}>{busy === 'csv' ? 'Exporting…' : 'Export CSV'}</Button><Button variant="secondary" disabled={!!busy} onClick={() => exportFile('xlsx')}>{busy === 'xlsx' ? 'Exporting…' : 'Export XLSX'}</Button></div></div><p id="sheet-help" className="border-b border-slate-100 px-5 py-3 text-xs leading-6 text-slate-500">Scroll horizontally to see all questions. Open a reference to review an application. Earlier question labels and option meanings are preserved for each response. Private image previews stay in this admin view; exports contain text answers.</p>
            <div role="region" aria-label="Form response spreadsheet" aria-describedby="sheet-help" tabIndex={0} className="max-h-[70vh] overflow-auto focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary-600"><table className="w-max min-w-full border-collapse text-left text-sm"><thead className="sticky top-0 z-20 bg-slate-100 text-xs text-slate-700"><tr><th scope="col" className="border-b border-r border-slate-200 p-3">#</th><th scope="col" className="sticky left-0 z-30 w-44 min-w-44 max-w-44 sm:w-52 sm:min-w-52 sm:max-w-52 border-b border-r border-slate-200 bg-slate-100 p-3">Registration reference</th>{['Contact email', 'Status', 'Submitted (Asia/Dhaka)', 'Form version', ...data.columns.map(field => field.label)].map((label, index) => <th scope="col" key={index < 4 ? label : data.columns[index - 4].key} className="min-w-44 max-w-64 break-words border-b border-r border-slate-200 p-3 font-semibold">{label}</th>)}</tr></thead><tbody>{data.results.map((row, rowIndex) => <tr key={row.id} className="group"><td className="border-b border-r border-slate-200 bg-slate-50 p-3 align-top text-xs text-slate-500">{(data.page_number - 1) * data.page_size + rowIndex + 1}</td><th scope="row" className="sticky left-0 z-10 w-44 min-w-44 max-w-44 sm:w-52 sm:min-w-52 sm:max-w-52 border-b border-r border-slate-200 bg-white p-3 align-top font-normal group-hover:bg-primary-50"><Link to={`/admin/submissions/${row.id}`} className="break-all font-mono text-xs font-semibold text-primary-700 underline underline-offset-4">{row.reference_number}</Link></th><td className="max-w-64 break-all border-b border-r border-slate-200 p-3 align-top">{row.applicant_email || '—'}</td><td className="border-b border-r border-slate-200 p-3 align-top"><StatusBadge status={row.status} /></td><td className="border-b border-r border-slate-200 p-3 align-top text-xs">{displayReviewDate(row.submitted_at)}</td><td className="border-b border-r border-slate-200 p-3 align-top text-xs">Version {row.schema_version}</td>{data.columns.map(column => {
                const field = row.form_schema.fields.find(field => field.key === column.key);
                return <td key={column.key} className="min-w-44 max-w-72 whitespace-pre-wrap break-words border-b border-r border-slate-200 p-3 align-top text-slate-700">{!field ? <span className="text-slate-400">—</span> : <>{field.label !== column.label && <p className="mb-2 text-xs text-slate-500">Asked as: {field.label}</p>}{field.field_type === 'file' ? fileCell(row, field) : answerLabel(field, row.answers[field.key])}</>}</td>;
            })}</tr>)}</tbody></table></div>{!data.results.length && <div className="px-5 py-12 text-center"><p className="font-semibold text-primary-900">No responses found</p><p className="mt-2 text-sm text-slate-500">Responses will appear here after applicants submit this form, or try changing your filters.</p></div>}</section><nav aria-label="Sheet pages" className="mt-5 flex items-center justify-between gap-3"><Button variant="secondary" disabled={!data.previous} onClick={() => filter('page', String(data.page_number - 1))}>Previous</Button><p className="text-sm text-slate-500">Page {data.page_number} of {data.total_pages}</p><Button variant="secondary" disabled={!data.next} onClick={() => filter('page', String(data.page_number + 1))}>Next</Button></nav></>}
        {image && <Dialog title="Private image preview" description="Visible only to authorized event administrators and reviewers." wide onClose={() => setImage(null)}><PrivateImage key={image.id} file={image} large /><div className="mt-5 text-right"><Button variant="secondary" onClick={() => setImage(null)}>Close preview</Button></div></Dialog>}
    </>;
}

export default function FormSheetsPage() {
    const { formId } = useParams();
    const navigate = useNavigate();
    const forms = useResource('/admin/review/forms/', true);
    return <><PageHeader title="Registration sheets" description="A separate response sheet for each form, with every question and protected image previews." /><ErrorNotice error={forms.error} onRetry={forms.reload} />
        {forms.loading ? <Loading label="Loading your forms…" /> : forms.data && <><div className="admin-panel mb-6"><Control label="Choose registration sheet" as="select" value={formId || ''} onChange={event => navigate(event.target.value ? `/admin/sheets/${event.target.value}` : '/admin/sheets')}><option value="">Choose a form</option>{forms.data.map(form => <option key={form.id} value={form.id}>{form.title} — {form.event_title || form.event_slug}</option>)}</Control></div>{!formId && (forms.data.length ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{forms.data.map(form => <Link key={form.id} className="admin-panel transition hover:border-primary-300" to={`/admin/sheets/${form.id}`}><p className="mb-2 text-xs text-slate-500">{form.event_title || form.event_slug}</p><h2 className="break-words text-lg text-primary-900">{form.title}</h2><p className="mt-4 text-sm font-semibold text-primary-700">{form.submission_count ?? 0} responses · Open sheet →</p></Link>)}</div> : <EmptyState title="No forms available" description="Forms for your assigned events will appear here." />)}</>}
        {formId && !forms.loading && !forms.error && <ResponseSheet key={formId} formId={formId} />}
    </>;
}
