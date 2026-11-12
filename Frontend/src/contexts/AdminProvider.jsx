import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../services/api';
import { AdminContext } from './AdminContext';

export default function AdminProvider({ children }) {
    const [session, setSession] = useState({ checking: true, administrator: null, error: null });
    const navigationGuardRef = useRef(null);
    const registerLeaveGuard = useCallback(guard => {
        navigationGuardRef.current = guard;
        return () => { if (navigationGuardRef.current === guard) navigationGuardRef.current = null; };
    }, []);
    const refresh = useCallback(async () => {
        try {
            const data = await api.session();
            setSession({ checking: false, administrator: data.authenticated ? data.administrator : null, error: null });
        } catch (error) {
            setSession({ checking: false, administrator: null, error });
        }
    }, []);
    useEffect(() => {
        let active = true;
        api.session().then(data => {
            if (active) setSession({ checking: false, administrator: data.authenticated ? data.administrator : null, error: null });
        }).catch(error => { if (active) setSession({ checking: false, administrator: null, error }); });
        return () => { active = false; };
    }, []);
    async function login(username, password) {
        await api.login(username, password);
        const data = await api.session();
        if (!data.authenticated) throw new ApiError(403, {}, 'Your browser could not retain the session. Check cookie and API proxy settings.');
        setSession({ checking: false, administrator: data.administrator, error: null });
    }
    async function logout() {
        await api.logout();
        setSession({ checking: false, administrator: null, error: null });
    }
    const roles = session.administrator?.roles || [];
    return <AdminContext.Provider value={{ ...session, refresh, login, logout, navigationGuardRef, registerLeaveGuard,
        isSuper: roles.includes('Super Admin'), canManage: roles.some(role => ['Super Admin', 'Event Admin'].includes(role)),
    }}>{children}</AdminContext.Provider>;
}
