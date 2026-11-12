import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AdminContext } from '../../contexts/AdminContext';
import FormBuilderPage from '../../pages/admin/FormBuilderPage';
import { api, ApiError } from '../../services/api';
import { newField } from './schema';
vi.mock('../../services/api', async importOriginal => ({ ...await importOriginal(), api: { get: vi.fn(), patch: vi.fn(), post: vi.fn() } }));
const original = { id: 7, event: 1, title: 'Delegate Registration', slug: 'delegates', form_type: 'custom', description: '', opens_at: null, closes_at: null, capacity: null, allow_multiple_submissions: false, status: 'draft', fields: [] };
function renderBuilder(form = original, denied = false) {
    if (denied) api.get.mockRejectedValue(new ApiError(403, { detail: 'Access denied.' }));
    else api.get.mockResolvedValue(structuredClone(form));
    api.patch.mockImplementation(async (_path, data) => ({ ...structuredClone(form), ...data }));
    return render(<AdminContext.Provider value={{ canManage: true, isSuper: true, navigationGuardRef: { current: null } }}><MemoryRouter initialEntries={['/admin/forms/7']}><Routes><Route path="/admin/forms/:id" element={<FormBuilderPage />} /></Routes></MemoryRouter></AdminContext.Provider>);
}
async function addQuestion(user, name = 'Short text') {
    await user.click(screen.getByRole('button', { name: /Add your first question|^＋ Add question$/ }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: new RegExp(name) }));
}
beforeEach(() => vi.clearAllMocks());
describe('no-code form builder', () => {
    it('adds, edits, requires and saves a real field payload', async () => {
        const user = userEvent.setup(); renderBuilder();
        await screen.findByRole('heading', { name: 'Delegate Registration' });
        await addQuestion(user);
        await user.type(screen.getByLabelText(/Question label/), 'Full name');
        await user.click(screen.getByLabelText('Required question'));
        await user.click(screen.getByRole('button', { name: 'Save draft' }));
        await screen.findByText('Draft saved.');
        expect(api.patch).toHaveBeenCalledWith('/admin/forms/7/', expect.objectContaining({ fields: [expect.objectContaining({ label: 'Full name', required: true, field_type: 'short_text', display_order: 0 })] }));
        expect(api.patch.mock.calls[0][1].fields[0].key).toMatch(/^question_/);
    });
    it('publishes only after the current draft is successfully saved', async () => {
        const user = userEvent.setup();
        api.post.mockResolvedValue({ version: 3 });
        renderBuilder({ ...original, fields: [{ ...newField(), label: 'Full name' }] });
        await screen.findByLabelText(/Question label/);
        await user.click(screen.getByRole('button', { name: /Publish form/ }));
        await user.click(screen.getByRole('button', { name: 'Save and publish' }));
        await screen.findByText('Version 3 published. Existing responses are preserved.');
        expect(api.post).toHaveBeenCalledWith('/admin/forms/7/publish/');
        expect(api.patch.mock.invocationCallOrder[0]).toBeLessThan(api.post.mock.invocationCallOrder[0]);
    });
    it('keeps publication from running after a failed save and displays the field error', async () => {
        const user = userEvent.setup(); renderBuilder({ ...original, fields: [newField()] });
        await screen.findByLabelText(/Question label/);
        api.patch.mockRejectedValue(new ApiError(400, { fields: [{ label: ['This field may not be blank.'] }] }));
        await user.click(screen.getByRole('button', { name: /Publish form/ }));
        await user.click(screen.getByRole('button', { name: 'Save and publish' }));
        await waitFor(() => expect(screen.getByLabelText(/Question label/)).toHaveAttribute('aria-invalid', 'true'));
        expect(screen.getAllByText(/This field may not be blank/).length).toBeGreaterThan(0);
        expect(api.post).not.toHaveBeenCalled();
    });
    it('edits choice labels and previews without sending answers', async () => {
        const user = userEvent.setup(); renderBuilder();
        await screen.findByRole('heading', { name: 'Delegate Registration' });
        await addQuestion(user, 'Dropdown');
        await user.type(screen.getByLabelText(/Question label/), 'Preferred committee');
        await user.clear(screen.getByLabelText('Option 1'));
        await user.type(screen.getByLabelText('Option 1'), 'General Assembly');
        await user.click(screen.getByRole('button', { name: 'Preview' }));
        const preview = screen.getByRole('dialog', { name: 'Form preview' });
        expect(within(preview).getByRole('option', { name: 'General Assembly' })).toBeInTheDocument();
        expect(api.post).not.toHaveBeenCalled();
        expect(api.patch).not.toHaveBeenCalled();
    });
    it('reorders stable keys and requires confirmation before deleting a draft field', async () => {
        const user = userEvent.setup();
        const first = { ...newField(), label: 'First' }, second = { ...newField(), label: 'Second', display_order: 1 };
        renderBuilder({ ...original, fields: [first, second] });
        await screen.findByLabelText(/Question label/);
        await user.click(screen.getByRole('button', { name: 'Move question 2 up' }));
        await user.click(screen.getByRole('button', { name: 'Save draft' }));
        await screen.findByText('Draft saved.');
        expect(api.patch.mock.calls[0][1].fields.map(field => field.key)).toEqual([second.key, first.key]);
        await user.click(screen.getByRole('button', { name: 'Delete question 1' }));
        await user.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(screen.getByRole('button', { name: 'Delete question 2' })).toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Delete question 1' }));
        await user.click(screen.getByRole('button', { name: 'Delete question' }));
        expect(screen.queryByRole('button', { name: 'Delete question 2' })).not.toBeInTheDocument();
    });
    it('shows access denied without fabricating a form after a forbidden response', async () => {
        renderBuilder(original, true);
        await screen.findByText('Access denied or session expired');
        expect(screen.queryByLabelText('Form title')).not.toBeInTheDocument();
    });
});
