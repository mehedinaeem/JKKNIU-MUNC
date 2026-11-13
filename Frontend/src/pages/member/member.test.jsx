import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import MemberPortal from './MemberPortal';
import { api } from '../../services/api';
vi.mock('../../services/api', () => ({ api: { post: vi.fn(), get: vi.fn(), publicGet: vi.fn(), memberLogin: vi.fn() }, apiUrl: path => `/api${path}` }));
function show(mode) { return render(<MemoryRouter><MemberPortal mode={mode} /></MemoryRouter>); }
beforeEach(() => { vi.clearAllMocks(); window.history.replaceState(null, '', '/'); });
describe('membership portal', () => {
    it('distinguishes application, private activation and member sign in', () => {
        show('join');
        expect(screen.getByRole('link', { name: /Start an application/ })).toHaveAttribute('href', '/join/apply');
        expect(screen.getByRole('link', { name: /Activate your account/ })).toHaveAttribute('href', '/join/activate');
        expect(screen.getByRole('link', { name: /Sign in/ })).toHaveAttribute('href', '/member/login');
        expect(screen.getByText('No. Activation requires a private invitation issued after independent identity confirmation.')).toBeInTheDocument();
    });
    it('does not offer registration-number account activation', () => {
        show('activate');
        expect(screen.getByLabelText(/Private invitation token/)).toBeRequired();
        expect(screen.queryByLabelText(/registration number/i)).not.toBeInTheDocument();
    });
    it('removes a private capability from browser URL and requires matching passwords', async () => {
        window.history.replaceState(null, '', '/join/activate#token=private-token-not-stored-in-browser-history');
        show('activate');
        expect(window.location.hash).toBe('');
        const user = userEvent.setup();
        await user.type(screen.getByLabelText(/^New password/), 'A-strong-password-123');
        await user.type(screen.getByLabelText(/^Confirm new password/), 'different-password-123');
        await user.click(screen.getByRole('button', { name: 'Activate account' }));
        await waitFor(() => expect(screen.getByText(/Passwords must match/)).toBeVisible());
        expect(api.post).not.toHaveBeenCalled();
    });
    it('uses a generic password recovery acknowledgement', async () => {
        api.post.mockResolvedValue({ detail: 'If an eligible account exists, recovery instructions will be sent to its verified email.' });
        show('forgot');
        const user = userEvent.setup();
        await user.type(screen.getByLabelText(/Registration number or verified email/), 'unknown@example.invalid');
        await user.click(screen.getByRole('button', { name: 'Request recovery instructions' }));
        expect(await screen.findByText(/If an eligible account exists/)).toBeVisible();
        expect(api.post).toHaveBeenCalledWith('/membership/password-reset/request/', { identifier: 'unknown@example.invalid' });
    });
    async function checkStudent() {
        api.post.mockResolvedValueOnce({ lookup_token: 'browser-bound-check', student: { registration_number: 'DEMO-001', full_name: 'Demo Student', department: 'English', student_id: '••••0001', session: '' } });
        show('apply');
        const user = userEvent.setup();
        await user.type(screen.getByLabelText(/University registration number/), 'DEMO-001');
        await user.click(screen.getByLabelText(/I consent to checking/));
        await user.click(screen.getByRole('button', { name: 'Show my student details' }));
        expect(await screen.findByRole('heading', { name: 'Is this you?' })).toBeVisible();
        expect(screen.getByText('Demo Student')).toBeVisible();
        expect(screen.queryByText('Academic session')).not.toBeInTheDocument();
        return user;
    }
    it('confirms student details and requires email; existing members skip motivation', async () => {
        const user = await checkStudent();
        await user.click(screen.getByRole('radio', { name: 'Yes, I am already a member' }));
        expect(screen.queryByLabelText(/Why would you like to join MUNC/)).not.toBeInTheDocument();
        expect(screen.getByLabelText(/Email address/)).toBeRequired();
        expect(screen.getByRole('button', { name: 'Submit application' })).toBeDisabled();
        await user.click(screen.getByLabelText(/Yes, this is me/));
        await user.type(screen.getByLabelText(/Email address/), 'student@example.invalid');
        api.post.mockResolvedValueOnce({ detail: 'Application request received. After review and approval, the club will email you a link to activate your account.', reference: 'test-reference' });
        await user.click(screen.getByRole('button', { name: 'Submit application' }));
        await waitFor(() => expect(api.post).toHaveBeenLastCalledWith('/membership/apply/', expect.objectContaining({ is_existing_member: true, motivation: '', identity_confirmed: true, contact_email: 'student@example.invalid', lookup_token: 'browser-bound-check' })));
        expect(await screen.findByText(/test-reference/)).toBeVisible();
    });
    it('requires a joining reason only for new members and clears it when selecting existing', async () => {
        const user = await checkStudent();
        await user.click(screen.getByRole('radio', { name: 'No, I would like to join' }));
        const reason = screen.getByLabelText(/Why would you like to join MUNC/);
        expect(reason).toBeRequired();
        await user.type(reason, 'I would like to learn diplomacy.');
        await user.click(screen.getByRole('radio', { name: 'Yes, I am already a member' }));
        expect(screen.queryByLabelText(/Why would you like to join MUNC/)).not.toBeInTheDocument();
        await user.click(screen.getByRole('radio', { name: 'No, I would like to join' }));
        expect(screen.getByLabelText(/Why would you like to join MUNC/)).toHaveValue('');
    });
    it('can reject the student record and check a different registration number', async () => {
        const user = await checkStudent();
        await user.click(screen.getByRole('button', { name: 'No, change registration number' }));
        expect(screen.queryByText('Demo Student')).not.toBeInTheDocument();
        expect(screen.queryByLabelText(/Yes, this is me/)).not.toBeInTheDocument();
        expect(screen.getByLabelText(/University registration number/)).not.toHaveAttribute('readonly');
        expect(screen.getByRole('button', { name: 'Show my student details' })).toBeVisible();
    });

});
