// Register before BrowserRouter's history listener. No interception occurs unless
// an editor explicitly registers unsaved work; public navigation is unaffected.
let activeGuard;
let restoring = false;
if (typeof window !== 'undefined') window.addEventListener('popstate', event => {
    if (restoring) {
        restoring = false;
        event.stopImmediatePropagation();
        return;
    }
    if (!activeGuard) return;
    const target = event.state?.idx;
    const current = activeGuard.index;
    if (typeof target !== 'number' || typeof current !== 'number' || target === current) return;
    if (!activeGuard.confirmLeave()) {
        event.stopImmediatePropagation();
        restoring = true;
        window.history.go(current - target);
    } else activeGuard.index = target;
}, true);

export function registerNavigationGuard(confirmLeave) {
    const guard = { index: window.history.state?.idx, confirmLeave };
    activeGuard = guard;
    return () => { if (activeGuard === guard) activeGuard = undefined; };
}
