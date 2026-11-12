export function errorText(value) {
    if (!value) return '';
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) return value.map(errorText).filter(Boolean).join(' ');
    if (typeof value === 'object') return Object.entries(value).map(([key, item]) => `${key}: ${errorText(item)}`).join(' ');
    return String(value);
}
export const slugify = text => text.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 230);
export function toDhakaInput(iso) {
    if (!iso) return '';
    const parts = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Dhaka', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(iso));
    return parts.replace(' ', 'T');
}
export const toApiDate = value => value ? `${value.length === 16 ? `${value}:00` : value}+06:00` : null;
export const displayDate = value => value ? new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Dhaka', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value)) : 'Not set';
