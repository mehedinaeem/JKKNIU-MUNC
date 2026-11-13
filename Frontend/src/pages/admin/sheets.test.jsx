import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { api, privateImage } from '../../services/api';
import FormSheetsPage from './FormSheetsPage';
vi.mock('../../services/api', () => ({ api: { get: vi.fn(), list: vi.fn() }, privateImage: vi.fn(), downloadPrivate: vi.fn() }));
const columns = [{ key: 'name', label: 'Preferred name', field_type: 'short_text' }, { key: 'committee', label: 'Committee', field_type: 'dropdown' }, { key: 'photo', label: 'Photo', field_type: 'file' }, { key: 'institution', label: 'Institution', field_type: 'short_text' }];
const data = { form: { id: 1, title: 'Delegate Registration', slug: 'delegates', event_title: 'Conference' }, columns, count: 1, page_number: 1, page_size: 20, total_pages: 1, next: null, previous: null,
    results: [{ id: 'submission-id', reference_number: 'JM-SHEET', applicant_email: 'private@example.com', status: 'submitted', submitted_at: '2026-11-12T10:00:00Z', schema_version: 1,
        answers: { name: 'Sheet applicant', committee: 'a' }, files: [{ id: 7, field_key: 'photo', content_type: 'image/png', original_filename: 'photo.png' }],
        form_schema: { fields: [{ ...columns[0], label: 'Original full name' }, { ...columns[1], options: [{ value: 'a', label: 'Historical committee' }] }, columns[2]] } }] };
let revoke;
beforeEach(() => {
    vi.clearAllMocks();
    api.list.mockResolvedValue([{ id: 1, title: 'Delegate Registration', event_title: 'Conference' }, { id: 2, title: 'Executive Board', event_title: 'Conference' }]);
    api.get.mockResolvedValue(structuredClone(data));
    privateImage.mockResolvedValue(new Blob(['test-image'], { type: 'image/png' }));
    revoke = vi.fn();
    const BaseURL = URL;
    vi.stubGlobal('URL', class extends BaseURL { static createObjectURL = vi.fn(() => 'blob:test-private-image'); static revokeObjectURL = revoke; });
});
afterEach(() => vi.unstubAllGlobals());
function mount() { return render(<MemoryRouter initialEntries={['/admin/sheets/1']}><Routes><Route path="/admin/sheets/:formId" element={<FormSheetsPage />} /></Routes></MemoryRouter>); }

it('shows all question columns, historical labels and choices, and applicant review links', async () => {
    mount();
    expect(await screen.findByRole('columnheader', { name: 'Institution' })).toBeVisible();
    expect(screen.getByText('Asked as: Original full name')).toBeVisible();
    expect(screen.getByText('Historical committee')).toBeVisible();
    expect(screen.getByRole('link', { name: 'JM-SHEET' })).toHaveAttribute('href', '/admin/submissions/submission-id');
    expect(screen.getByText('private@example.com')).toBeVisible();
});

it('loads private images and revokes blob URLs after closing previews or leaving the sheet', async () => {
    const user = userEvent.setup();
    const view = mount();
    await screen.findByText('Sheet applicant');
    await waitFor(() => expect(privateImage).toHaveBeenCalledWith('/submission-files/7/preview/', expect.anything()));
    expect(await screen.findByRole('img', { name: 'Uploaded image preview' })).toHaveAttribute('src', 'blob:test-private-image');
    await user.click(screen.getByRole('button', { name: 'Enlarge image' }));
    expect(await screen.findByRole('img', { name: 'Private uploaded image' })).toBeVisible();
    expect(privateImage).toHaveBeenCalledWith('/submission-files/7/preview/?size=large', expect.anything());
    await user.click(screen.getByRole('button', { name: 'Close preview' }));
    expect(revoke).toHaveBeenCalledTimes(1);
    view.unmount();
    expect(revoke).toHaveBeenCalledTimes(2);
});

it('switches to a separate sheet with no applicant data from the previous form', async () => {
    const user = userEvent.setup();
    mount(); await screen.findByText('Sheet applicant');
    api.get.mockResolvedValue({ ...data, form: { ...data.form, id: 2, title: 'Executive Board' }, results: [], count: 0 });
    await user.selectOptions(screen.getByRole('combobox', { name: 'Choose registration sheet' }), '2');
    expect(await screen.findByText('No responses found')).toBeVisible();
    expect(screen.queryByText('private@example.com')).not.toBeInTheDocument();
    expect(api.get).toHaveBeenLastCalledWith('/admin/forms/2/sheet/?', expect.anything());
});

it('hides the spreadsheet when server permissions deny access', async () => {
    api.get.mockRejectedValue({ status: 404, errors: { detail: 'Not found.' } });
    mount(); expect(await screen.findByRole('alert')).toHaveTextContent('Not found.');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
});
