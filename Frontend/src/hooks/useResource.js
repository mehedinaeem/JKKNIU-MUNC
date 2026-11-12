import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';

export default function useResource(path, collection = false, anonymous = false) {
    const [generation, setGeneration] = useState(0);
    const [state, setState] = useState({ key: null, data: null, error: null });
    const key = `${path}:${collection}:${anonymous}:${generation}`;
    useEffect(() => {
        const controller = new AbortController();
        if (path) {
            const load = anonymous ? (collection ? api.publicList : api.publicGet) : (collection ? api.list : api.get);
            load(path, { signal: controller.signal }).then(data => setState({ key, data, error: null }))
                .catch(error => { if (error.name !== 'AbortError') setState({ key, data: null, error }); });
        }
        return () => controller.abort();
    }, [path, collection, anonymous, key]);
    const reload = useCallback(() => setGeneration(value => value + 1), []);
    return { ...(state.key === key ? state : { data: null, error: null }), loading: !!path && state.key !== key, reload };
}
