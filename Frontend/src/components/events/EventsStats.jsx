export default function EventsStats({ total, years, categories }) {
    return <dl className="grid grid-cols-3 gap-3 sm:gap-8 border-t border-white/15 pt-6 mt-8 max-w-xl">
        {[[total, 'Total Events'], [years, 'Years of Activities'], [categories, 'Categories']].map(([value, label]) => (
            <div key={label}><dt className="text-xs sm:text-sm text-slate-300">{label}</dt><dd className="text-2xl sm:text-3xl font-heading font-semibold text-accent-400 mt-1">{value}</dd></div>
        ))}
    </dl>;
}
