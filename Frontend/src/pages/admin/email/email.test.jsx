import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import EmailApp from './EmailApp';
import { EmailPreview, RichEmailEditor } from './EmailUI';
import { api } from '../../../services/api';
vi.mock('../../../services/api', () => ({ api: { get: vi.fn(), list: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
beforeEach(() => vi.clearAllMocks());
it('keeps provider acceptance separate from confirmed delivery and shows disabled transport', async () => {
    api.get.mockResolvedValue({ statuses: { pending: 4 }, total_queued: 8, accepted: 3, delivered: 1, pending: 4, failed: 1, unknown: 0, enabled: false, daily_limit: 300, transactional_reserve: 50, approximate_remaining_quota: 297 });
    render(<MemoryRouter initialEntries={['/admin/email']}><Routes><Route path="/admin/email/*" element={<EmailApp />} /></Routes></MemoryRouter>);
    expect(await screen.findByText(/Email transport is disabled/)).toBeVisible();
    expect(screen.getByText('Accepted by provider').parentElement).toHaveTextContent('3');
    expect(screen.getByText('Confirmed delivered').parentElement).toHaveTextContent('1');
});
it('isolates previews in a sandbox with no script, image or external-resource permissions', () => {
    render(<EmailPreview data={{ subject: 'Preview', html_content: '<p>Hello Example</p>', text_content: 'Hello Example' }} onClose={() => {}} />);
    const frame = screen.getByTitle('Sanitized email preview');
    expect(frame).toHaveAttribute('sandbox', '');
    expect(frame.getAttribute('srcdoc')).toContain("default-src 'none'");
});
it('initializes the rich editor with approved HTML and exposes keyboard-accessible formatting', () => {
    render(<RichEmailEditor value="<p>Hello {{full_name}}</p>" onChange={() => {}} />);
    expect(screen.getByRole('textbox', { name: 'Formatted email' })).toHaveTextContent('Hello {{full_name}}');
    expect(screen.getByRole('button', { name: 'Bold', exact: true })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Bullet list', exact: true })).toBeEnabled();
});
