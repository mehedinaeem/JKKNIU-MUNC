import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import EventsPage from './pages/EventsPage';
import EventDetailsPage from './pages/EventDetailsPage';
import GalleryPage from './pages/GalleryPage';
import ContactPage from './pages/ContactPage';

/**
 * App Component
 * Main application component with React Router configuration
 */
function App() {
  return (
    <Router>
      <Routes>
        {/* All routes wrapped in Layout component */}
        <Route path="/" element={<Layout />}>
          {/* Home Page - Default route */}
          <Route index element={<HomePage />} />

          {/* About Page */}
          <Route path="about" element={<AboutPage />} />

          {/* Events Page */}
          <Route path="events" element={<EventsPage />} />
          <Route path="events/:slug" element={<EventDetailsPage />} />

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
