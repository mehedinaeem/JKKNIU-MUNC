import './services/navigationGuard';
import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import EventsPage from './pages/EventsPage';
import EventDetailsPage from './pages/EventDetailsPage';
import GalleryPage from './pages/GalleryPage';
import ContactPage from './pages/ContactPage';

const MemberPortal = lazy(() => import('./pages/member/MemberPortal'));
const AdminApp = lazy(() => import('./pages/admin/AdminApp'));
const EventRegistrationPage = lazy(() => import('./pages/registration/EventRegistrationPage'));
const EventRegistrationFormPage = lazy(() => import('./pages/registration/EventRegistrationFormPage'));
const RegistrationConfirmationPage = lazy(() => import('./pages/registration/RegistrationConfirmationPage'));
function RegistrationRoute({ children }) {
  return <Suspense fallback={<div role="status" className="pt-32 text-center">Loading registration…</div>}>{children}</Suspense>;
}

/**
 * App Component
 * Main application component with React Router configuration
 */
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/admin/*" element={<Suspense fallback={<div role="status" className="p-8 text-center text-primary-900">Loading administration…</div>}><AdminApp /></Suspense>} />
        {/* All routes wrapped in Layout component */}
        <Route path="/" element={<Layout />}>
          {/* Home Page - Default route */}
          <Route index element={<HomePage />} />

          {/* About Page */}
          <Route path="about" element={<AboutPage />} />

          {/* Events Page */}
          <Route path="events" element={<EventsPage />} />
          <Route path="events/:slug" element={<EventDetailsPage />} />

          <Route path="events/:slug/register" element={<RegistrationRoute><EventRegistrationPage /></RegistrationRoute>} />
          <Route path="events/:slug/register/:formSlug" element={<RegistrationRoute><EventRegistrationFormPage /></RegistrationRoute>} />
          <Route path="events/:slug/register/:formSlug/confirmation" element={<RegistrationRoute><RegistrationConfirmationPage /></RegistrationRoute>} />

          <Route path="join" element={<RegistrationRoute><MemberPortal key="join" mode="join" /></RegistrationRoute>} />
          <Route path="join/apply" element={<RegistrationRoute><MemberPortal key="apply" mode="apply" /></RegistrationRoute>} />
          <Route path="join/activate" element={<RegistrationRoute><MemberPortal key="activate" mode="activate" /></RegistrationRoute>} />
          <Route path="member/login" element={<RegistrationRoute><MemberPortal key="login" mode="login" /></RegistrationRoute>} />
          <Route path="member/forgot-password" element={<RegistrationRoute><MemberPortal key="forgot" mode="forgot" /></RegistrationRoute>} />
          <Route path="member/reset-password" element={<RegistrationRoute><MemberPortal key="reset" mode="reset" /></RegistrationRoute>} />
          <Route path="member/dashboard" element={<RegistrationRoute><MemberPortal key="dashboard" mode="dashboard" /></RegistrationRoute>} />
          <Route path="member/profile" element={<RegistrationRoute><MemberPortal key="profile" mode="profile" /></RegistrationRoute>} />
          <Route path="member/settings" element={<RegistrationRoute><MemberPortal key="settings" mode="settings" /></RegistrationRoute>} />

          {/* Gallery Page */}
          <Route path="gallery" element={<GalleryPage />} />

          {/* Contact Page */}
          <Route path="contact" element={<ContactPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
