const configuredBase = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');
let csrfToken;
let csrfRequest;

export class ApiError extends Error {
    constructor(status, errors, message) {
        super(message || (typeof errors?.detail === 'string' ? errors.detail : 'The request could not be completed.'));
        this.name = 'ApiError';
        this.status = status;
        this.errors = errors || {};
    }
}

export const apiUrl = path => `${configuredBase}${path}`;

async function request(path, { method = 'GET', data, signal, credentials = 'include' } = {}) {
    if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Use an API-relative path.');
    const headers = { Accept: 'application/json' };
    if (data !== undefined) headers['Content-Type'] = 'application/json';
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers['X-CSRFToken'] = await getCSRF();
    let response;
    try {
        response = await fetch(`${configuredBase}${path}`, {
            method, headers, credentials, cache: 'no-store', redirect: 'error',
            body: data === undefined ? undefined : JSON.stringify(data), signal,
        });
    } catch (error) {
        if (error.name === 'AbortError') throw error;
        throw new ApiError(0, {}, 'Cannot connect to the API. Check your connection and API configuration.');
    }
    if (response.status === 204) return null;
    const json = response.headers.get('content-type')?.includes('application/json');
    const body = json ? await response.json() : null;
    if (!json) throw new ApiError(response.status, {}, 'The API returned an unexpected response. Check VITE_API_BASE_URL or the API proxy.');
    if (!response.ok) {
        if (response.status === 403 && String(body?.detail).includes('CSRF')) csrfToken = undefined;
        throw new ApiError(response.status, body,
            response.status === 429 ? 'Too many attempts. Please wait before trying again.' : undefined);
    }
    return body;
}

async function getCSRF() {
    if (csrfToken) return csrfToken;
    if (!csrfRequest) {
        csrfRequest = request('/admin/auth/csrf/').then(data => {
            if (!data.csrf_token) throw new ApiError(0, {}, 'Could not initialize secure requests.');
            csrfToken = data.csrf_token;
            return csrfToken;
        }).finally(() => { csrfRequest = undefined; });
    }
    return csrfRequest;
}

async function list(path, { signal, credentials = 'include' } = {}) {
    const results = [];
    let nextPath = path;
    for (let page = 0; page < 100; page++) {
        const data = await request(nextPath, { signal, credentials });
        if (!Array.isArray(data.results)) throw new ApiError(0, {}, 'The API did not return a paginated collection.');
        results.push(...data.results);
        if (!data.next) return results;
        // Keep pagination on the configured API/proxy, never follow a supplied host.
        const next = new URL(data.next, window.location.origin);
        nextPath = `${path.split('?')[0]}${next.search}`;
    }
    throw new ApiError(0, {}, 'This collection is too large to load. Narrow your selection.');
}

export const api = {
    get: (path, options) => request(path, options),
    post: (path, data = {}) => request(path, { method: 'POST', data }),
    patch: (path, data) => request(path, { method: 'PATCH', data }),
    list,
    publicGet: (path, options) => request(path, { ...options, credentials: 'omit' }),
    publicList: (path, options) => list(path, { ...options, credentials: 'omit' }),
    session: () => request('/admin/auth/me/'),
    async login(username, password) {
        const data = await request('/admin/auth/login/', { method: 'POST', data: { username, password } });
        csrfToken = data.csrf_token; // Django rotates CSRF state on login.
        return data;
    },
    async memberLogin(identifier, password) {
        const data = await request('/membership/login/', { method: 'POST', data: { identifier, password } });
        csrfToken = data.csrf_token;
        return data;
    },
    async memberLogout() {
        await request('/membership/logout/', { method: 'POST', data: {} });
        csrfToken = undefined;
    },
    async uploadMemberPhoto(file) {
        const data = new FormData(); data.append('photo', file);
        const response = await fetch(apiUrl('/membership/photo/'), { method: 'POST', credentials: 'include', cache: 'no-store', redirect: 'error', headers: { 'X-CSRFToken': await getCSRF() }, body: data });
        const body = await response.json();
        if (!response.ok) throw new ApiError(response.status, body);
        return body;
    },
    async logout() {
        await request('/admin/auth/logout/', { method: 'POST', data: {} });
        csrfToken = undefined;
    },
};


export async function downloadPrivate(path, filename) {
    if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Use an API-relative path.');
    let response;
    try { response = await fetch(apiUrl(path), { credentials: 'include', cache: 'no-store', redirect: 'error', headers: { Accept: '*/*' } }); }
    catch { throw new ApiError(0, {}, 'The download could not connect. Please retry.'); }
    if (!response.ok) {
        let detail = {};
        try { detail = await response.json(); } catch { /* Non-JSON gateway error. */ }
        throw new ApiError(response.status, detail);
    }
    if (!response.headers.get('content-disposition')?.startsWith('attachment;')) throw new ApiError(0, {}, 'Unexpected download response. Check the API proxy.');
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = filename; document.body.append(anchor); anchor.click(); anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}


export async function privateImage(path, { signal } = {}) {
    if (!/^\/submission-files\/\d+\/preview\/(\?size=large)?$/.test(path)) throw new Error('Use a private image preview path.');
    let response;
    try { response = await fetch(apiUrl(path), { signal, credentials: 'include', cache: 'no-store', redirect: 'error', headers: { Accept: 'image/png, image/jpeg, application/json' } }); }
    catch (error) { if (error.name === 'AbortError') throw error; throw new ApiError(0, {}, 'Image preview could not connect.'); }
    if (!response.ok) {
        let detail = {};
        try { detail = await response.json(); } catch { /* Gateway response. */ }
        throw new ApiError(response.status, detail, 'Image preview is unavailable.');
    }
    if (!['image/png', 'image/jpeg'].includes(response.headers.get('content-type'))) throw new ApiError(0, {}, 'Unexpected image response.');
    return response.blob();
}
