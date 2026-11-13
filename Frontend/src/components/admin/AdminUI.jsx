import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { errorText } from './adminUtils';

export function Button({ variant = 'primary', className = '', children, type = 'button', ...props }) {
    return <button type={type} className={`admin-button admin-button-${variant} ${className}`} {...props}>{children}</button>;
}
export function Control({ label, error, hint, as = 'input', children, id: suppliedId, className = '', ...props }) {
    const generatedId = useId();
    const id = suppliedId || generatedId;
    const Tag = as;
    return <div className={`min-w-0 ${className}`}>
        <label className="admin-label" htmlFor={id}>{label}{props.required && <span aria-hidden="true" className="text-red-600"> *</span>}</label>
        <Tag id={id} className="admin-input" aria-invalid={!!error || undefined} aria-describedby={(error || hint) ? `${id}-description` : undefined} {...props}>{children}</Tag>
        {(error || hint) && <p id={`${id}-description`} className={error ? 'admin-field-error' : 'admin-hint'}>{errorText(error) || hint}</p>}
    </div>;
}
export function StatusBadge({ status }) {
    const colors = { accepted: 'bg-blue-50 text-blue-800 ring-blue-200', delivered: 'bg-emerald-50 text-emerald-800 ring-emerald-200', verified: 'bg-emerald-50 text-emerald-800 ring-emerald-200', unknown: 'bg-red-50 text-red-800 ring-red-200', failed: 'bg-red-50 text-red-800 ring-red-200', hard_bounced: 'bg-red-50 text-red-800 ring-red-200', blocked: 'bg-red-50 text-red-800 ring-red-200', approved: 'bg-emerald-50 text-emerald-800 ring-emerald-200', rejected: 'bg-red-50 text-red-800 ring-red-200', under_review: 'bg-blue-50 text-blue-800 ring-blue-200', submitted: 'bg-primary-50 text-primary-800 ring-primary-200', shortlisted: 'bg-purple-50 text-purple-800 ring-purple-200', waitlisted: 'bg-amber-50 text-amber-800 ring-amber-200', published: 'bg-emerald-50 text-emerald-800 ring-emerald-200', draft: 'bg-amber-50 text-amber-900 ring-amber-200', closed: 'bg-slate-100 text-slate-700 ring-slate-200', archived: 'bg-slate-100 text-slate-600 ring-slate-200', completed: 'bg-blue-50 text-blue-800 ring-blue-200', cancelled: 'bg-red-50 text-red-800 ring-red-200' };
    return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold capitalize ring-1 ring-inset ${colors[status] || colors.draft}`}>{status?.replaceAll('_', ' ')}</span>;
}
export function PageHeader({ eyebrow = 'MUNC administration', title, description, children }) {
    return <header className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div className="min-w-0"><p className="mb-2 text-xs font-bold uppercase tracking-[.18em] text-primary-600">{eyebrow}</p><h1 className="break-words text-2xl font-bold text-primary-900 sm:text-3xl">{title}</h1>{description && <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">{description}</p>}</div>
        {children && <div className="flex flex-wrap gap-2 shrink-0">{children}</div>}
    </header>;
}
export function Loading({ label = 'Loading…' }) {
    return <div role="status" className="flex min-h-40 items-center justify-center gap-3 text-sm text-slate-500"><span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-primary-600 motion-reduce:animate-none" />{label}</div>;
}
export function ErrorNotice({ error, title, onRetry, id }) {
    if (!error) return null;
    const denied = error.status === 403;
    return <div id={id} tabIndex={-1} role="alert" className="admin-error mb-5">
        <h2 className="font-semibold">{title || (denied ? 'Access denied or session expired' : error.status === 404 ? 'This item is unavailable' : 'Please check the following')}</h2>
        <p className="mt-1 text-sm break-words">{errorText(error.errors?.detail) || errorText(error.errors) || error.message || errorText(error)}</p>
        {denied && <p className="mt-2 text-sm">Sign out and sign back in if your session expired, or ask a Super Admin to check your event assignment.</p>}
        {onRetry && <Button variant="secondary" className="mt-3" onClick={onRetry}>Try again</Button>}
    </div>;
}
export function EmptyState({ title, description, children }) {
    return <div className="admin-panel py-14 text-center"><div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-50 text-2xl text-primary-600" aria-hidden="true">▤</div><h2 className="text-lg text-primary-900">{title}</h2><p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">{description}</p>{children && <div className="mt-5">{children}</div>}</div>;
}
export function Notice({ children }) {
    return children ? <p role="status" className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{children}</p> : null;
}
export function Dialog({ title, description, children, onClose, wide = false, busy = false }) {
    const ref = useRef(null);
    const titleId = useId();
    useEffect(() => {
        const previous = document.activeElement;
        const element = ref.current;
        element.showModal();
        const overflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => { element.close(); document.body.style.overflow = overflow; previous?.isConnected && previous.focus(); };
    }, []);
    return createPortal(<dialog ref={ref} aria-labelledby={titleId} className={`admin-app admin-dialog ${wide ? 'admin-dialog-wide' : ''}`}
        onCancel={event => { event.preventDefault(); if (!busy) onClose(); }}>
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-5 sm:p-6"><div><h2 id={titleId} className="text-xl text-primary-900">{title}</h2>{description && <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>}</div><Button variant="ghost" aria-label="Close dialog" disabled={busy} onClick={onClose}>✕</Button></div>
        <div className="p-5 sm:p-6">{children}</div>
    </dialog>, document.body);
}
