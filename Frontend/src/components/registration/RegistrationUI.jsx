import { Link } from 'react-router-dom';

export function RegistrationHero({ title, eyebrow = 'JKKNIU Model United Nations Club', children }) {
    return <header className="bg-primary-900 py-12 text-white sm:py-16"><div className="mx-auto max-w-5xl px-4 sm:px-6"><Link to="/events" className="text-sm font-medium text-slate-300 hover:text-accent-300">← Events archive</Link><p className="mb-4 mt-8 text-xs font-semibold uppercase tracking-[.18em] text-accent-300">{eyebrow}</p><h1 className="text-3xl font-bold leading-tight sm:text-4xl">{title}</h1>{children && <div className="mt-5 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">{children}</div>}</div></header>;
}
export function RegistrationLoading() {
    return <div role="status" className="registration-panel flex min-h-40 items-center justify-center gap-3 text-sm text-slate-500"><span aria-hidden="true" className="h-5 w-5 animate-spin rounded-full border-2 border-primary-100 border-t-primary-600 motion-reduce:animate-none" />Loading registration details…</div>;
}
export function RegistrationUnavailable({ error, reason, onRetry }) {
    const missing = error?.status === 404 || !error;
    return <section className="registration-panel text-center" role="alert"><span className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full bg-accent-50 text-2xl text-accent-700" aria-hidden="true">i</span><h2 className="text-xl text-primary-900">{missing ? 'Registration unavailable' : 'Unable to load registration'}</h2><p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-slate-600">{reason || (missing ? 'This form may be closed, unpublished, or unavailable for this event. Please check with the organisers.' : 'We could not reach registration services. Please check your connection and try again.')}</p><div className="mt-6 flex flex-wrap justify-center gap-3">{!missing && onRetry && <button type="button" className="btn-primary" onClick={onRetry}>Try again</button>}<Link to="/events" className="rounded-lg border border-slate-300 px-5 py-3 text-sm font-semibold text-primary-700">Browse events</Link></div></section>;
}
