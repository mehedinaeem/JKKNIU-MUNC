import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { storeAttempt, submitRegistration } from './registration';
let requests;
class TestXHR {
    constructor() { this.upload = {}; requests.push(this); }
    open(method, url) { this.method = method; this.url = url; }
    setRequestHeader() {}
    send(body) { this.body = body; }
}
beforeEach(() => { requests = []; vi.stubGlobal('XMLHttpRequest', TestXHR); sessionStorage.clear(); });
afterEach(() => vi.unstubAllGlobals());
it('sends multipart schema answers and files with the same idempotency key', async () => {
    const file = new File(['image'], 'photo.png', { type: 'image/png' });
    const progress = vi.fn();
    const promise = submitRegistration('form', { version: 2, applicant_email: 'a@example.com', answers: { name: 'A' }, submission_key: 'test-key' }, { photo: file }, progress);
    const request = requests[0];
    expect(request.url).toBe('/api/forms/form/submit/');
    expect(request.withCredentials).toBe(false);
    expect(JSON.parse(request.body.get('payload')).submission_key).toBe('test-key');
    expect(request.body.get('photo').name).toBe('photo.png');
    request.upload.onprogress({ lengthComputable: true, loaded: 5, total: 10 });
    expect(progress).toHaveBeenCalledWith(50);
    request.status = 201; request.responseText = JSON.stringify({ reference_number: 'JM-ACTUAL' }); request.onload();
    await expect(promise).resolves.toEqual({ reference_number: 'JM-ACTUAL' });
});
it('never treats a network failure or malformed success response as confirmation', async () => {
    const first = submitRegistration('form', { answers: {} }, {}); requests[0].onerror();
    await expect(first).rejects.toMatchObject({ status: 0 });
    const second = submitRegistration('form', { answers: {} }, {});
    requests[1].status = 200; requests[1].responseText = '{}'; requests[1].onload();
    await expect(second).rejects.toMatchObject({ status: 0 });
});
it('persists only non-PII receipt metadata in this tab', () => {
    storeAttempt('event', 'form', { reference_number: 'JM-REFERENCE', version: 1, applicant_email: 'private@example.com', answers: { phone: '+8801712345678' } });
    const stored = sessionStorage.getItem('munc-registration:/api:event:form');
    expect(JSON.parse(stored)).toEqual({ reference_number: 'JM-REFERENCE', version: 1 });
    expect(stored).not.toContain('private@example.com');
    expect(stored).not.toContain('phone');
});
