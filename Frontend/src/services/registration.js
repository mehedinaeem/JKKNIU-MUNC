import { apiUrl, ApiError } from './api';

// An explicit retry uses the same opaque key and identical payload. Never retry automatically.
export function submitRegistration(slug, { version, applicant_email, answers, submission_key }, files, onProgress = () => {}) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', apiUrl(`/forms/${encodeURIComponent(slug)}/submit/`));
        xhr.timeout = 120000;
        xhr.withCredentials = false; // Public endpoint ignores administrator sessions.
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.upload.onprogress = event => onProgress(event.lengthComputable ? Math.min(100, Math.round(event.loaded / event.total * 100)) : null);
        const uncertain = message => reject(new ApiError(0, {}, message));
        xhr.onerror = () => uncertain('The connection was interrupted. We could not confirm the result.');
        xhr.ontimeout = () => uncertain('The server took too long to confirm your application.');
        xhr.onabort = () => uncertain('The request was interrupted before confirmation.');
        xhr.onload = () => {
            let data;
            try { data = JSON.parse(xhr.responseText); } catch { return uncertain('An unexpected response was received. We could not confirm the result.'); }
            if (xhr.status >= 200 && xhr.status < 300) {
                if (typeof data.reference_number !== 'string' || !data.reference_number.trim() || data.reference_number.length > 160) return uncertain('The server did not return a registration reference.');
                resolve(data);
            } else reject(new ApiError(xhr.status, data, xhr.status === 429 ? 'Too many attempts. Please wait before retrying.' : undefined));
        };
        const body = new FormData();
        body.append('payload', JSON.stringify({ version, applicant_email, answers, submission_key }));
        Object.entries(files).forEach(([key, file]) => body.append(key, file, file.name));
        xhr.send(body);
    });
}

const storageKey = (event, form) => `munc-registration:${apiUrl('')}:${event}:${form}`;
export function readAttempt(event, form) {
    try { return JSON.parse(sessionStorage.getItem(storageKey(event, form))) || {}; } catch { return {}; }
}
export function storeAttempt(event, form, data) {
    // Only opaque attempt/version/reference metadata, never contact details, answers or files.
    try { sessionStorage.setItem(storageKey(event, form), JSON.stringify({ submission_key: data.submission_key, version: data.version, reference_number: data.reference_number })); } catch { /* Memory-only flow remains usable. */ }
}
