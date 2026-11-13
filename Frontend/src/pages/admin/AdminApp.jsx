import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import AdminProvider from '../../contexts/AdminProvider';
import useAdminAuth from '../../hooks/useAdminAuth';
import AdminLayout from '../../components/admin/AdminLayout';
import { ErrorNotice, Loading, PageHeader } from '../../components/admin/AdminUI';
import LoginPage from './LoginPage';
import DashboardPage from './DashboardPage';
import EventsManagementPage from './EventsManagementPage';
import EventEditorPage from './EventEditorPage';
import FormsManagementPage from './FormsManagementPage';
import ApplicationsPage from './ApplicationsPage';
import ApplicationDetailPage from './ApplicationDetailPage';
import FormSheetsPage from './FormSheetsPage';
import EmailApp from './email/EmailApp';
import MembersApp from './MembersApp';
import FormBuilderPage from './FormBuilderPage';
import '../../components/admin/admin.css';

function ProtectedRoutes() {
    const auth = useAdminAuth();
    const location = useLocation();
    if (auth.checking) return <div className="admin-app admin-shell"><Loading label="Checking your administrator session…" /></div>;
    if (auth.error) return <div className="admin-app admin-shell p-6"><ErrorNotice error={auth.error} onRetry={auth.refresh} /></div>;
    if (!auth.administrator) return <Navigate to="/admin/login" state={{ from: location.pathname + location.search }} replace />;
    return <Outlet />;
}
function ManagementRoutes() {
    const { canManage } = useAdminAuth();
    return canManage ? <Outlet /> : <><PageHeader title="Access denied" description="Your reviewer role allows assigned application review. Managing forms and email requires Event Admin or Super Admin access." /><p className="text-sm text-slate-500">Ask a Super Admin if your role or assignment needs to change.</p></>;
}
function AdminHome() {
    const { administrator } = useAdminAuth();
    return administrator?.roles?.length && administrator.roles.every(role => role === 'Membership Admin') ? <Navigate to="/admin/members" replace /> : <DashboardPage />;
}
export default function AdminApp() {
    return <AdminProvider><Routes>
        <Route path="login" element={<LoginPage />} />
        <Route element={<ProtectedRoutes />}><Route element={<AdminLayout />}>
            <Route index element={<AdminHome />} />
            <Route path="members/*" element={<MembersApp />} />
            <Route path="events" element={<EventsManagementPage />} />
            <Route path="events/new" element={<EventEditorPage />} />
            <Route path="events/:id" element={<EventEditorPage />} />
            <Route path="sheets" element={<FormSheetsPage />} />
            <Route path="sheets/:formId" element={<FormSheetsPage />} />
            <Route path="submissions" element={<ApplicationsPage />} />
            <Route path="submissions/:id" element={<ApplicationDetailPage />} />
            <Route element={<ManagementRoutes />}>
                <Route path="email/*" element={<EmailApp />} />
                <Route path="email-campaigns" element={<Navigate to="/admin/email/campaigns" replace />} />
                <Route path="forms" element={<FormsManagementPage />} />
                <Route path="forms/:id" element={<FormBuilderPage />} />
            </Route>
            <Route path="*" element={<PageHeader title="Page not found" description="Choose a workspace from the administration menu." />} />
        </Route></Route>
    </Routes></AdminProvider>;
}
