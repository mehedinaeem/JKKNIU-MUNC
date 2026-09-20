import { useState } from 'react';

export default function EventImage({ src, mobile, cover, alt, className = '', loading = 'lazy' }) {
    const [attempt, setAttempt] = useState(0);
    const candidates = [...new Set([src, cover, '/mun-logo.png'].filter(Boolean))];
    const fallback = candidates[Math.min(attempt, candidates.length - 1)];
    return (
        <picture className={className}>
            {mobile && attempt === 0 && <source media="(max-width: 640px)" srcSet={mobile} />}
            <img src={fallback} alt={alt} loading={loading} decoding="async"
                style={fallback === '/mun-logo.png' ? { objectFit: 'contain', padding: '1rem' } : undefined}
                onError={() => setAttempt(value => Math.min(value + 1, candidates.length - 1))} />
        </picture>
    );
}
