export default function EventFilters({ filters, onChange, years, categories, onReset }) {
    const active = filters.search || filters.year || filters.category;
    return (
        <div className="event-filters motion-safe:animate-fade-in-up">
            <div className="grid gap-4 md:grid-cols-[1.4fr_.7fr_1fr]">
                <label className="event-filter-label">Search the archive
                    <input type="search" placeholder="Search events, topics…" value={filters.search} onChange={e => onChange('search', e.target.value)} />
                </label>
                <label className="event-filter-label">Year
                    <select aria-label="Year" value={filters.year} onChange={e => onChange('year', e.target.value)}>
                        <option value="">All Years</option>
                        {years.map(year => <option key={year} value={year}>{year}</option>)}
                    </select>
                </label>
                <label className="event-filter-label">Category
                    <select aria-label="Category" value={filters.category} onChange={e => onChange('category', e.target.value)}>
                        <option value="">All Categories</option>
                        {categories.map(category => <option key={category}>{category}</option>)}
                    </select>
                </label>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 mt-4 min-h-11 text-sm">
                <span key={`${filters.year}-${filters.category}`} className="event-filter-indicator motion-safe:animate-fade-in">{active ? 'Filtered archive' : 'The complete collection'}</span>
                <button className="event-reset" onClick={onReset} disabled={!active}>Reset filters <span aria-hidden="true">↺</span></button>
            </div>
        </div>
    );
}
