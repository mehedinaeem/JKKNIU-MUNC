import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { api, downloadPrivate } from '../../services/api';
import ApplicationDetailPage from './ApplicationDetailPage';
import ApplicationsPage from './ApplicationsPage';
vi.mock('../../services/api', () => ({ api: { get: vi.fn(), list: vi.fn(), post: vi.fn(), patch: vi.fn() }, downloadPrivate: vi.fn() }));
const initial = { id: 'test-id', event: 1, reference_number: 'JM-TEST', event_title: 'Conference', form_title: 'Delegates', applicant_email: 'private@example.com', status: 'submitted', submitted_at: '2026-11-12T10:00:00Z', answers: { arbitrary_key: 'Applicant name', committee: 'ga' },
    form_schema: { fields: [{ key: 'arbitrary_key', label: 'Historical name label', field_type: 'short_text' }, { key: 'committee', label: 'Committee', field_type: 'dropdown', options: [{ value: 'ga', label: 'Historical committee label' }] }, { key: 'cv', label: 'CV', field_type: 'file' }] },
    files: [{ id: 4, field_key: 'cv', content_type: 'application/pdf', file_size: 200, original_filename: 'cv.pdf' }], history: [], reviewer_notes: [] };
function detail() { return render(<MemoryRouter initialEntries={['/admin/submissions/test-id']}><Routes><Route path="/admin/submissions/:id" element={<ApplicationDetailPage />} /></Routes></MemoryRouter>); }
beforeEach(() => { vi.clearAllMocks(); api.get.mockResolvedValue(structuredClone(initial)); });

it('renders historical dynamic answers and downloads only the authorized API file', async () => {
    detail();
    expect(await screen.findByText('Historical name label')).toBeVisible();
    expect(screen.getByText('Applicant name')).toBeVisible();
    expect(screen.getByText('Historical committee label')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Download private file' }));
    expect(downloadPrivate).toHaveBeenCalledWith('/submission-files/4/', 'application-JM-TEST-4.pdf');
});

it('updates status and appends private notes, with server errors kept visible', async () => {
    const user = userEvent.setup();
    detail(); await screen.findByText('Applicant name');
    api.get.mockResolvedValue({ ...initial, status: 'under_review' });
    await user.selectOptions(screen.getByLabelText('Review status'), 'under_review');
    await user.click(screen.getByRole('button', { name: 'Update status' }));
    await screen.findByText('Application status updated.');
    expect(api.patch).toHaveBeenCalledWith('/admin/submissions/test-id/status/', { status: 'under_review' });
    api.post.mockRejectedValueOnce({ status: 400, errors: { body: ['Review note rejected.'] } });
    await user.type(screen.getByRole('textbox', { name: 'Note', exact: true }), 'Private assessment');
    await user.click(screen.getByRole('button', { name: 'Add private note' }));
    expect(await screen.findAllByText('Review note rejected.')).not.toHaveLength(0);
    expect(screen.getByRole('textbox', { name: 'Note', exact: true })).toHaveValue('Private assessment');
    api.post.mockResolvedValueOnce({});
    api.get.mockResolvedValue({ ...initial, status: 'under_review', reviewer_notes: [{ id: 1, body: 'Private assessment', author_name: 'Reviewer', created_at: '2026-11-12T11:00:00Z' }] });
    await user.click(screen.getByRole('button', { name: 'Add private note' }));
    expect(await screen.findByText('Private reviewer note added.')).toBeVisible();
    expect(screen.getByText('Private assessment')).toBeVisible();
    expect(screen.getByRole('textbox', { name: 'Note', exact: true })).toHaveValue('');
});

it('does not render applicant details on denied access', async () => {
    api.get.mockRejectedValue({ status: 403, errors: { detail: 'Assigned event access required.' } });
    detail();
    expect(await screen.findByRole('alert')).toHaveTextContent('Assigned event access required.');
    expect(screen.queryByText('private@example.com')).not.toBeInTheDocument();
});

it('uses server pagination and matching filters for search and exports', async () => {
    const user = userEvent.setup();
    api.list.mockResolvedValue([]);
    api.get.mockResolvedValue({ count: 30, results: [initial], next: '/api/admin/submissions/?page=2', previous: null });
    render(<MemoryRouter><ApplicationsPage /></MemoryRouter>);
    await screen.findByText('JM-TEST');
    await user.click(screen.getByRole('button', { name: 'Next', exact: true }));
    await waitFor(() => expect(api.get).toHaveBeenLastCalledWith('/admin/submissions/?page=2', expect.anything()));
    await user.type(screen.getByRole('searchbox', { name: 'Search applications' }), 'Applicant name');
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }));
    await waitFor(() => expect(api.get).toHaveBeenLastCalledWith('/admin/submissions/?search=Applicant+name', expect.anything()));
    await user.click(screen.getByRole('button', { name: 'Export XLSX' }));
    expect(downloadPrivate).toHaveBeenCalledWith('/admin/submissions/export/?search=Applicant+name&file_format=xlsx', 'munc-applications.xlsx');
});
