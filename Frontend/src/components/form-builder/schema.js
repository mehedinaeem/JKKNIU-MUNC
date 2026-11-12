import { toApiDate } from '../admin/adminUtils';
export const FIELD_TYPES = [
    ['short_text', 'Short text', 'Aa', 'A name or a brief response'],
    ['long_text', 'Long text', '¶', 'An explanation or statement'],
    ['email', 'Email', '@', 'A valid email address'],
    ['phone', 'Phone number', '☎', 'A contact number'],
    ['integer', 'Integer', '#', 'A whole number'],
    ['decimal', 'Decimal number', '1.5', 'A number with decimals'],
    ['date', 'Date', '▦', 'A calendar date'],
    ['dropdown', 'Dropdown', '⌄', 'Choose one from a list'],
    ['radio', 'Radio buttons', '◉', 'Show every single-choice option'],
    ['checkboxes', 'Checkboxes', '☑', 'Choose more than one option'],
    ['file', 'File upload', '↥', 'An image or PDF document'],
    ['url', 'URL', '↗', 'A website link'],
    ['consent', 'Consent checkbox', '✓', 'An explicit agreement'],
];
export const selectionTypes = ['dropdown', 'radio', 'checkboxes'];
export const textTypes = ['short_text', 'long_text', 'email', 'phone', 'url'];
const identifier = prefix => `${prefix}_${crypto.randomUUID().replaceAll('-', '')}`;
export const newOption = (label = '') => ({ value: identifier('choice'), label });
export function newField(type = 'short_text') {
    return { key: identifier('question'), field_type: type, label: '', help_text: '', placeholder: '', required: false, display_order: 0,
        default_value: null, validation: {}, options: selectionTypes.includes(type) ? [newOption('Option 1'), newOption('Option 2')] : [],
        allowed_extensions: type === 'file' ? ['pdf', 'png', 'jpg', 'jpeg'] : [], max_file_size: type === 'file' ? 5 * 1024 * 1024 : null };
}
export function changeType(field, type) {
    const fresh = newField(type);
    return { ...field, field_type: type, default_value: null, validation: {},
        options: selectionTypes.includes(type) && selectionTypes.includes(field.field_type) ? field.options : fresh.options,
        allowed_extensions: fresh.allowed_extensions, max_file_size: fresh.max_file_size };
}
export function serializeFields(fields) {
    return fields.map((field, index) => ({ ...field, display_order: index,
        validation: Object.fromEntries(Object.entries(field.validation || {}).filter(([, value]) => value !== '' && value != null).map(([key, value]) => [key, ['min_length', 'max_length', 'min_choices', 'max_choices'].includes(key) ? Number(value) : value])),
    }));
}

export function formPayload(form) {
    return { title: form.title, description: form.description, slug: form.slug, form_type: form.form_type,
        opens_at: toApiDate(form.opens_at), closes_at: toApiDate(form.closes_at),
        capacity: form.capacity === '' ? null : Number(form.capacity), allow_multiple_submissions: form.allow_multiple_submissions,
        fields: serializeFields(form.fields) };
}
