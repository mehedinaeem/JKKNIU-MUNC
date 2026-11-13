import { useState } from 'react';
import { api } from '../../../services/api';
import { ErrorNotice } from '../../../components/admin/AdminUI';
import { EmailPreview } from './EmailUI';

export default function useEmailPreview() {
    const [preview, setPreview] = useState(null);
    const [error, setError] = useState(null);
    async function show(content) {
        setError(null);
        try { setPreview(await api.post('/admin/email/templates/preview/', content)); }
        catch (failure) { setError(failure); }
    }
    return { show, output: <><ErrorNotice error={error} />{preview && <EmailPreview data={preview} onClose={() => setPreview(null)} />}</> };
}
