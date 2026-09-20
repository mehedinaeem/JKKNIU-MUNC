const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

// Use only explicit, recognized date formats. Unknown precision sorts after known dates.
// This key is never used to change the supplied display date.
function dateKey(value = '') {
    const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (iso) return Number(iso[2]) * 100 + Number(iso[3]);
    const named = /^(?:Announced )?(?:(\d{1,2})(?:[–-]\d{1,2})? )?([A-Za-z]+) \d{4}$/.exec(value);
    if (!named) return 0;
    const month = months.indexOf(named[2]) + 1;
    return month ? month * 100 + Number(named[1] || 0) : 0;
}

export function newestFirst(a, b) {
    return b.year - a.year || dateKey(b.date) - dateKey(a.date);
}

export function displayDate(event) {
    return event.endDate && event.endDate !== event.date ? `${event.date} – ${event.endDate}` : event.date;
}
