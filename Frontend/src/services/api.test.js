import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });
beforeEach(() => { vi.resetModules(); vi.stubEnv('VITE_API_BASE_URL', '/api'); vi.stubGlobal('fetch', vi.fn()); });
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
describe('session API client', () => {
    it('uses credentials and the rotated CSRF token without browser storage', async () => {
        fetch.mockResolvedValueOnce(json({ csrf_token: 'before-login' }))
            .mockResolvedValueOnce(json({ authenticated: true, csrf_token: 'after-login' }))
            .mockResolvedValueOnce(json({ title: 'Saved' }));
        const { api } = await import('./api');
        await api.login('admin', 'test-only-password');
        await api.patch('/admin/forms/7/', { title: 'Saved' });
        expect(fetch.mock.calls[1][1].headers['X-CSRFToken']).toBe('before-login');
        expect(fetch.mock.calls[2][1].headers['X-CSRFToken']).toBe('after-login');
        expect(fetch.mock.calls.every(([, options]) => options.credentials === 'include')).toBe(true);
        expect(localStorage.length).toBe(0);
    });
    it('does not automatically repeat a failed write', async () => {
        fetch.mockResolvedValueOnce(json({ csrf_token: 'token' }))
            .mockResolvedValueOnce(json({ detail: 'CSRF verification failed.' }, 403));
        const { api } = await import('./api');
        await expect(api.patch('/admin/forms/7/', { title: 'Draft' })).rejects.toMatchObject({ status: 403 });
        expect(fetch).toHaveBeenCalledTimes(2);
    });
    it('keeps paginated requests on the configured proxy', async () => {
        fetch.mockResolvedValueOnce(json({ results: [{ id: 1 }], next: 'https://backend.example/api/admin/events/?page=2' }))
            .mockResolvedValueOnce(json({ results: [{ id: 2 }], next: null }));
        const { api } = await import('./api');
        expect(await api.list('/admin/events/')).toEqual([{ id: 1 }, { id: 2 }]);
        expect(fetch.mock.calls[1][0]).toBe('/api/admin/events/?page=2');
    });
    it('reports an unconfigured proxy instead of treating an HTML page as success', async () => {
        fetch.mockResolvedValue(new Response('<html>SPA fallback</html>', { headers: { 'content-type': 'text/html' } }));
        const { api } = await import('./api');
        await expect(api.session()).rejects.toThrow(/API returned an unexpected response/);
    });
});
