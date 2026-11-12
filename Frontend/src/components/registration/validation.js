export const SUPPORTED_TYPES = ['short_text', 'long_text', 'email', 'phone', 'integer', 'decimal', 'date', 'dropdown', 'radio', 'checkboxes', 'file', 'url', 'consent'];
const MIME = { pdf: 'application/pdf', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg' };
export function initialAnswers(fields) {
    return Object.fromEntries(fields.filter(field => field.default_value != null && !['file', 'consent'].includes(field.field_type)).map(field => [field.key, structuredClone(field.default_value)]));
}
export function emailError(value) {
    return typeof value !== 'string' || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? 'Enter a valid email address.' : '';
}
export function validateRegistration(fields, answers, files, email) {
    const errors = {};
    if (emailError(email)) errors.applicant_email = emailError(email);
    let totalSize = 0;
    let fileCount = 0;
    for (const field of fields) {
        const value = field.field_type === 'file' ? files[field.key] : answers[field.key];
        const kind = field.field_type;
        const rules = field.validation || {};
        const empty = value == null || value === '' || (typeof value === 'string' && !value.trim()) || (Array.isArray(value) && !value.length);
        if (!SUPPORTED_TYPES.includes(kind)) { errors[field.key] = 'This question is not supported. Please contact the organisers.'; continue; }
        if (empty || (kind === 'consent' && value !== true)) {
            if (field.required) errors[field.key] = kind === 'consent' ? 'Please give your consent to continue.' : 'This question is required.';
            continue;
        }
        let error = '';
        if (kind === 'file') {
            fileCount++; totalSize += value.size;
            const extension = value.name.split('.').pop().toLowerCase();
            if (!(field.allowed_extensions || []).includes(extension) || !MIME[extension]) error = 'Choose an allowed image or PDF file.';
            else if (value.type !== MIME[extension]) error = 'The file type does not match its extension. Choose a valid image or PDF.';
            else if (!value.size || value.size > Math.min(field.max_file_size || 10485760, 10485760)) error = `Choose a nonempty file no larger than ${(field.max_file_size || 10485760) / 1048576} MiB.`;
        } else if (['dropdown', 'radio', 'checkboxes'].includes(kind)) {
            const allowed = new Set(field.options.map(option => option.value));
            if (kind === 'checkboxes') {
                if (!Array.isArray(value) || value.some(choice => !allowed.has(choice)) || new Set(value).size !== value.length) error = 'Choose valid options.';
                else if (value.length < (rules.min_choices || 0) || value.length > (rules.max_choices ?? allowed.size)) error = 'Check the number of selected options.';
            } else if (!allowed.has(value)) error = 'Choose one of the available options.';
        } else if (['integer', 'decimal'].includes(kind)) {
            const number = Number(value);
            if (!Number.isFinite(number) || Math.abs(number) > 1e18 || (kind === 'integer' && !Number.isInteger(number))) error = kind === 'integer' ? 'Enter a whole number.' : 'Enter a valid number.';
            else if ((rules.min_value != null && number < Number(rules.min_value)) || (rules.max_value != null && number > Number(rules.max_value))) error = 'The number is outside the allowed range.';
        } else if (kind === 'date') {
            if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(value)) || new Date(value).toISOString().slice(0, 10) !== value) error = 'Enter a valid date.';
            else if ((rules.min_date && value < rules.min_date) || (rules.max_date && value > rules.max_date)) error = 'The date is outside the allowed range.';
        } else if (kind !== 'consent') {
            if (typeof value !== 'string') error = 'Enter a valid text answer.';
            else if (value.length < (rules.min_length || 0) || value.length > (rules.max_length ?? (kind === 'long_text' ? 100000 : kind === 'short_text' ? 10000 : 1000))) error = 'Check the length of your answer.';
            else if (kind === 'email') error = emailError(value);
            else if (kind === 'phone' && (!/^\+?[0-9 ()-]{7,30}$/.test(value) || value.replace(/\D/g, '').length < 7 || value.replace(/\D/g, '').length > 15)) error = 'Enter a valid phone number, including country code if applicable.';
            else if (kind === 'url') {
                try { if (!['https:', 'http:'].includes(new URL(value).protocol)) error = 'Enter an HTTP or HTTPS website URL.'; } catch { error = 'Enter a valid website URL.'; }
            }
        }
        if (error) errors[field.key] = error;
    }
    if (totalSize > 20 * 1048576 || fileCount > 10) errors.files = 'Use no more than 10 files and 20 MiB of uploads in total.';
    return errors;
}
export function prepareAnswers(fields, answers) {
    return Object.fromEntries(fields.filter(field => field.field_type !== 'file' && answers[field.key] != null && answers[field.key] !== '' && !(typeof answers[field.key] === 'string' && !answers[field.key].trim()) && !(Array.isArray(answers[field.key]) && !answers[field.key].length)).map(field => [field.key, answers[field.key]]));
}

export function answerError(value) {
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) return value.map(answerError).join(' ');
    if (value && typeof value === 'object') return Object.values(value).map(answerError).join(' ');
    return '';
}
