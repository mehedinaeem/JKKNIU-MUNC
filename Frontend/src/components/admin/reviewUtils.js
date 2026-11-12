export const APPLICATION_STATUSES = ['submitted', 'under_review', 'shortlisted', 'approved', 'rejected', 'waitlisted'];
export const statusLabel = status => status.replaceAll('_', ' ').replace(/^./, char => char.toUpperCase());
export function answerLabel(field, value) {
    if (value == null || value === '') return 'No answer';
    if (field.field_type === 'consent') return value ? 'Consent given' : 'Consent not given';
    const option = value => field.options?.find(option => option.value === value)?.label || String(value);
    if (Array.isArray(value)) return value.map(option).join(', ') || 'No answer';
    if (['radio', 'dropdown'].includes(field.field_type)) return option(value);
    return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

export const displayReviewDate = value => value ? new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Dhaka', day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' }).format(new Date(value)) : 'Not recorded';
