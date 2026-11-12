import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import RegistrationForm from './RegistrationForm';
import EventRegistrationFormPage from '../../pages/registration/EventRegistrationFormPage';
import RegistrationConfirmationPage from '../../pages/registration/RegistrationConfirmationPage';
import { ApiError, api } from '../../services/api';
import { submitRegistration } from '../../services/registration';
import { validateRegistration } from './validation';
vi.mock('../../services/registration', async original => ({ ...await original(), submitRegistration: vi.fn() }));
vi.mock('../../services/api', async original => ({ ...await original(), api: { publicGet: vi.fn() } }));
const fields = [
    { key: 'name', label: 'Full name', field_type: 'short_text', required: true, validation: {}, options: [] },
    { key: 'email', label: 'Email', field_type: 'email', required: true, validation: {}, options: [] },
    { key: 'committee', label: 'Committee', field_type: 'dropdown', required: true, options: [{ value: 'a', label: 'Assembly' }], validation: {} },
    { key: 'consent', label: 'Data processing consent', field_type: 'consent', required: true, validation: {}, options: [] },
];
const definition = { id: 1, slug: 'delegates', event_slug: 'conference', version: 1, accepting_submissions: true, schema: { title: 'Delegate Registration', description: '', fields } };
function mount(form = definition) {
    api.publicGet.mockResolvedValue(form);
    return render(<MemoryRouter initialEntries={['/events/conference/register/delegates']}><Routes>
        <Route path="/events/:slug/register/:formSlug" element={<RegistrationForm definition={form} eventSlug="conference" onReload={vi.fn()} />} />
        <Route path="/events/:slug/register/:formSlug/confirmation" element={<RegistrationConfirmationPage />} />
    </Routes></MemoryRouter>);
}
async function fill(user) {
    await user.type(screen.getByRole('textbox', { name: 'Full name', exact: true }), 'Example applicant');
    await user.type(screen.getByRole('textbox', { name: 'Email', exact: true }), 'applicant@example.com');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Committee', exact: true }), 'a');
    await user.click(screen.getByRole('checkbox', { name: 'Data processing consent I agree', exact: true }));
}
beforeEach(() => { vi.clearAllMocks(); sessionStorage.clear(); });
it('shows required errors before making a submission', async () => {
    const user = userEvent.setup(); mount();
    await user.click(screen.getByRole('button', { name: /Submit application/ }));
    expect(submitRegistration).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox', { name: 'Full name', exact: true })).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getAllByText(/This question is required/).length).toBeGreaterThan(0);
});
it('uses schema choices and confirms only the reference returned by Django', async () => {
    const user = userEvent.setup(); submitRegistration.mockResolvedValue({ reference_number: 'JM-SERVER-REFERENCE' }); mount();
    await fill(user);
    await user.click(screen.getByRole('button', { name: /Submit application/ }));
    await screen.findByText('JM-SERVER-REFERENCE');
    expect(submitRegistration).toHaveBeenCalledWith('delegates', expect.objectContaining({ version: 1, applicant_email: 'applicant@example.com', answers: { name: 'Example applicant', email: 'applicant@example.com', committee: 'a', consent: true } }), {}, expect.any(Function));
    expect(sessionStorage.getItem('munc-registration:/api:conference:delegates')).not.toContain('applicant@example.com');
    expect(screen.getByText(/does not confirm selection/)).toBeInTheDocument();
});
it('prevents double clicks and reports upload progress while awaiting confirmation', async () => {
    const user = userEvent.setup(); let finish;
    submitRegistration.mockImplementation((_slug, _payload, _files, progress) => { progress(65); return new Promise(resolve => { finish = resolve; }); });
    mount(); await fill(user);
    await user.click(screen.getByRole('button', { name: /Submit application/ }));
    expect(screen.getByRole('button', { name: 'Processing…' })).toBeDisabled();
    expect(screen.getByRole('progressbar')).toHaveAttribute('value', '65');
    expect(submitRegistration).toHaveBeenCalledTimes(1);
    finish({ reference_number: 'JM-PROGRESS-REFERENCE' });
    await screen.findByText('JM-PROGRESS-REFERENCE');
});
it('keeps the same payload and key for an explicit retry after an uncertain result', async () => {
    const user = userEvent.setup();
    submitRegistration.mockRejectedValueOnce(new ApiError(0, {}, 'Connection lost')).mockResolvedValueOnce({ reference_number: 'JM-RETRY-REFERENCE' });
    mount(); await fill(user);
    await user.click(screen.getByRole('button', { name: /Submit application/ }));
    await screen.findByText('Confirmation not yet received');
    expect(screen.getByRole('textbox', { name: 'Full name', exact: true })).toBeDisabled();
    expect(submitRegistration).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: /Retry same application/ }));
    await screen.findByText('JM-RETRY-REFERENCE');
    expect(submitRegistration.mock.calls[1][1]).toEqual(submitRegistration.mock.calls[0][1]);
});
it('maps server-side answer errors back to the affected input', async () => {
    const user = userEvent.setup(); submitRegistration.mockRejectedValue(new ApiError(400, { answers: { name: ['Please use your full name.'] } }));
    mount(); await fill(user); await user.click(screen.getByRole('button', { name: /Submit application/ }));
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'Full name', exact: true })).toHaveAttribute('aria-invalid', 'true'));
    expect(screen.getAllByText(/Please use your full name/).length).toBeGreaterThan(0);
});
it('does not render a submit button for closed forms or another event’s form', async () => {
    api.publicGet.mockImplementation(path => Promise.resolve(path.startsWith('/events/') ? { title: 'Conference' } : { ...definition, accepting_submissions: false, unavailable_reason: 'Registration has closed.' }));
    render(<MemoryRouter initialEntries={['/events/conference/register/delegates']}><Routes><Route path="/events/:slug/register/:formSlug" element={<EventRegistrationFormPage />} /></Routes></MemoryRouter>);
    await screen.findByText('Registration has closed.');
    expect(screen.queryByRole('button', { name: /Submit application/ })).not.toBeInTheDocument();
});
it('validates selection, date, phone and file constraints without trusting them as server checks', () => {
    const questions = [
        { key: 'date', label: 'Date', field_type: 'date' }, { key: 'phone', label: 'Phone', field_type: 'phone' },
        { key: 'upload', label: 'Photo', field_type: 'file', allowed_extensions: ['png'], max_file_size: 2 },
        { ...fields[2], key: 'choice' },
    ];
    const errors = validateRegistration(questions, { date: '2027-02-30', phone: 'not-a-number', choice: 'unknown' }, { upload: new File(['oversize'], 'image.png', { type: 'image/png' }) }, 'bad-email');
    expect(Object.keys(errors)).toEqual(expect.arrayContaining(['date', 'phone', 'upload', 'choice', 'applicant_email']));
});
