import { registerNavigationGuard } from '../services/navigationGuard';
import { useContext, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { AdminContext } from '../contexts/AdminContext';

export default function useUnsavedChanges(dirty) {
    const registerLeaveGuard = useContext(AdminContext)?.registerLeaveGuard;
    const location = useLocation();
    useEffect(() => {
        if (!dirty) return;
        const ask = () => window.confirm('You have unsaved changes. Leave without saving?');
        const unregisterAdminGuard = registerLeaveGuard?.(ask);
        const unregister = registerNavigationGuard(ask);
        const beforeUnload = event => { event.preventDefault(); event.returnValue = ''; };
        const click = event => {
            const link = event.target.closest?.('a[href]');
            if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey
                || link.target === '_blank' || link.hasAttribute('download')) return;
            const target = new URL(link.href);
            if (target.origin === window.location.origin && target.pathname === window.location.pathname && target.search === window.location.search) return;
            if (!ask()) { event.preventDefault(); event.stopPropagation(); }
        };
        window.addEventListener('beforeunload', beforeUnload);
        document.addEventListener('click', click, true);
        return () => {
            unregister();
            unregisterAdminGuard?.();
            window.removeEventListener('beforeunload', beforeUnload);
            document.removeEventListener('click', click, true);
        };
    }, [dirty, location.key, registerLeaveGuard]);
}
