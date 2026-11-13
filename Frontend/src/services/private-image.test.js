import { afterEach, expect, it, vi } from 'vitest';
import { privateImage } from './api';
afterEach(() => vi.unstubAllGlobals());
it('uses a credentialed no-store request and accepts only image responses', async () => {
    const blob = new Blob(['image'], { type: 'image/png' });
    const fetch = vi.fn().mockResolvedValue({ ok: true, headers: new Headers({ 'content-type': 'image/png' }), blob: async () => blob });
    vi.stubGlobal('fetch', fetch);
    expect(await privateImage('/submission-files/7/preview/')).toBe(blob);
    expect(fetch).toHaveBeenCalledWith('/api/submission-files/7/preview/', expect.objectContaining({ credentials: 'include', cache: 'no-store', redirect: 'error' }));
    fetch.mockResolvedValue({ ok: true, headers: new Headers({ 'content-type': 'text/html' }) });
    await expect(privateImage('/submission-files/7/preview/')).rejects.toThrow('Unexpected image response.');
});
it('rejects arbitrary URLs and denied image requests', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 403, json: async () => ({ detail: 'Denied' }) }));
    await expect(privateImage('https://example.com/private')).rejects.toThrow('Use a private image preview path.');
    expect(fetch).not.toHaveBeenCalled();
    await expect(privateImage('/submission-files/7/preview/')).rejects.toMatchObject({ status: 403 });
});
