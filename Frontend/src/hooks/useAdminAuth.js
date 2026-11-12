import { useContext } from 'react';
import { AdminContext } from '../contexts/AdminContext';
export default function useAdminAuth() {
    const value = useContext(AdminContext);
    if (!value) throw new Error('Administrator context is required.');
    return value;
}
