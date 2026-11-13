import { useEffect, useRef, useState } from 'react';
import { privateImage } from '../../services/api';

export default function PrivateImage({ file, large = false }) {
    const element = useRef(null);
    const [visible, setVisible] = useState(large || typeof IntersectionObserver === 'undefined');
    const [generation, setGeneration] = useState(0);
    const [result, setResult] = useState({ key: null, url: '', error: false });
    const key = `${file.id}:${large}:${generation}`;
    useEffect(() => {
        if (visible) return;
        const observer = new IntersectionObserver(entries => {
            if (entries.some(entry => entry.isIntersecting)) { setVisible(true); observer.disconnect(); }
        });
        observer.observe(element.current);
        return () => observer.disconnect();
    }, [visible]);
    useEffect(() => {
        if (!visible) return;
        const controller = new AbortController();
        let active = true, url;
        privateImage(`/submission-files/${file.id}/preview/${large ? '?size=large' : ''}`, { signal: controller.signal }).then(blob => {
            if (!active) return;
            url = URL.createObjectURL(blob);
            setResult({ key, url, error: false });
        }).catch(error => { if (active && error.name !== 'AbortError') setResult({ key, url: '', error: true }); });
        return () => { active = false; controller.abort(); if (url) URL.revokeObjectURL(url); };
    }, [visible, file.id, large, key]);
    const current = result.key === key;
    return <div ref={element} className={large ? 'flex min-h-40 items-center justify-center' : 'flex h-24 w-28 items-center justify-center rounded-lg bg-slate-50'}>
        {current && result.url ? <img src={result.url} alt={large ? 'Private uploaded image' : 'Uploaded image preview'} className={large ? 'max-h-[70vh] max-w-full object-contain' : 'h-24 w-28 rounded-lg object-contain'} /> : current && result.error ? <button type="button" className="px-2 text-xs font-semibold text-primary-700 underline" onClick={() => setGeneration(value => value + 1)}>Retry image</button> : <span role="status" className="px-2 text-xs text-slate-500">{visible ? 'Loading image…' : 'Image preview'}</span>}
    </div>;
}
