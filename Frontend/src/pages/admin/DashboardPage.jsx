import { Link } from 'react-router-dom';
import useAdminAuth from '../../hooks/useAdminAuth';
import useResource from '../../hooks/useResource';
import { EmptyState, ErrorNotice, Loading, PageHeader, StatusBadge } from '../../components/admin/AdminUI';
import { displayDate } from '../../components/admin/adminUtils';

export default function DashboardPage() {
    const { canManage, isSuper } = useAdminAuth();
    const events = useResource('/admin/events/', true);
    const metrics = useResource('/admin/dashboard/');
    const loading = events.loading || metrics.loading;
    const error = events.error || metrics.error;
    return <><PageHeader title="Your event workspace" description="Manage events, registration forms and assigned applications in one place.">{canManage && <Link className="admin-button admin-button-primary" to="/admin/forms?create=1">＋ Create a form</Link>}</PageHeader>
        <ErrorNotice error={error} onRetry={() => { events.reload(); metrics.reload(); }} />
        {loading ? <Loading label="Loading your workspace…" /> : !error && <>
            <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{[
                ['Total events', metrics.data?.total_events, '/admin/events'],
                ['Published registration forms', metrics.data?.published_forms, canManage ? '/admin/forms' : '/admin/submissions'],
                ['Total submissions', metrics.data?.total_submissions, '/admin/submissions'],
                ['New applications', metrics.data?.statuses.submitted, '/admin/submissions?status=submitted'],
                ['Applications under review', metrics.data?.statuses.under_review, '/admin/submissions?status=under_review'],
                ['Approved applicants', metrics.data?.statuses.approved, '/admin/submissions?status=approved'],
                ['Rejected applicants', metrics.data?.statuses.rejected, '/admin/submissions?status=rejected'],
            ].map(([label, count, to]) => <Link to={to} key={label} className="admin-panel block transition hover:border-primary-300"><p className="text-xs font-semibold text-slate-500">{label}</p><p className="mt-3 text-3xl font-bold text-primary-900">{count}</p></Link>)}</div>
            <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]"><section className="admin-panel"><div className="mb-6 flex items-center justify-between gap-3"><h2 className="text-lg text-primary-900">Events in your workspace</h2><Link className="text-sm font-semibold text-primary-600" to="/admin/events">All events →</Link></div>{events.data?.length ? <div className="divide-y divide-slate-100">{events.data.slice(0, 5).map(event => <Link to={`/admin/events/${event.id}`} key={event.id} className="flex flex-wrap items-center justify-between gap-3 py-4 first:pt-0"><div className="min-w-0"><h3 className="break-words text-sm font-semibold text-primary-900">{event.title}</h3><p className="mt-1 text-xs text-slate-500">{displayDate(event.start_date)} · {event.event_type}</p></div><StatusBadge status={event.status} /></Link>)}</div> : <EmptyState title="No events yet" description={isSuper ? 'Create an event to start welcoming applications.' : 'A Super Admin can assign an event to your account.'} />}</section>
            <section className="rounded-2xl bg-primary-900 p-6 text-white"><p className="text-xs font-semibold uppercase tracking-widest text-accent-300">A better first impression</p><h2 className="mt-4 text-2xl leading-snug">The right questions.<br />A smoother registration.</h2><p className="mt-4 text-sm leading-7 text-slate-300">Start with a draft, add your questions and preview the experience before publishing.</p>{canManage ? <Link className="admin-button mt-6 bg-accent-400 text-primary-900 hover:bg-accent-300" to="/admin/forms">Open form workspace →</Link> : <Link to="/admin/submissions" className="admin-button mt-6 bg-accent-400 text-primary-900">Review applications →</Link>}</section></div>
        </>}
    </>;
}
