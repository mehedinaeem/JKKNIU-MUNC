# JKKNIU MUN Club Website

A modern, responsive React frontend for the **JKKNIU Model United Nations Club** website built with Vite, Tailwind CSS 3, and React Router.

## 🚀 Quick Start

### Installation

```bash
# Navigate to the Frontend directory
cd Frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:5173/`

### Build for Production

```bash
npm run build
```

## 📁 Project Structure

```
Frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── Layout.jsx      # Main layout wrapper
│   │   ├── Navbar.jsx      # Sticky navigation
│   │   ├── HeroVideo.jsx   # Hero with video background
│   │   └── Footer.jsx      # Footer component
│   ├── pages/
│   │   ├── HomePage.jsx    # Landing page
│   │   ├── AboutPage.jsx   # About the club
│   │   ├── EventsPage.jsx  # Events listing
│   │   ├── GalleryPage.jsx # Photo gallery
│   │   └── ContactPage.jsx # Contact form
│   ├── data/
│   │   ├── events.js       # Sample events data
│   │   └── gallery.js      # Sample gallery data
│   ├── App.jsx             # Router configuration
│   ├── main.jsx            # Entry point
│   └── index.css           # Tailwind styles
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

## ✨ Features

- **Full-screen Hero** with autoplaying background video
- **Sticky Navigation** with mobile hamburger menu
- **5 Core Pages**: Home, About, Events, Gallery, Contact
- **Responsive Design** - Mobile-first approach
- **Modern Animations** - Smooth transitions and hover effects
- **University Branding** - Navy blue and gold color scheme
- **Accessible Components** - ARIA labels and semantic HTML

## 🎨 Tech Stack

- **React** (Vite)
- **Tailwind CSS 3**
- **React Router DOM**
- **Google Fonts** (Inter, Poppins)

## 📝 Pages Overview

| Page | Route | Description |
|------|-------|-------------|
| Home | `/` | Hero video, features, stats |
| About | `/about` | Mission, vision, timeline, team |
| Events | `/events` | Upcoming & past events |
| Gallery | `/gallery` | Photo gallery with lightbox |
| Contact | `/contact` | Contact form & info |

## 🔧 Customization

### Colors
Edit `tailwind.config.js` to customize the color scheme:
- `primary` - Navy blue shades
- `accent` - Gold/amber shades

### Video
Replace the hero video URL in `src/components/HeroVideo.jsx`

### Content
Update sample data in `src/data/events.js` and `src/data/gallery.js`

## 🚀 Netlify Deployment (CI/CD)

### Automatic Deployment

1. **Connect Repository**
   - Go to [Netlify](https://app.netlify.com)
   - Click "Add new site" → "Import an existing project"
   - Connect your GitHub account
   - Select `mehedinaeem/JKKNIU-MUNC` repository

2. **Configure Build Settings**
   - Base directory: `Frontend`
   - Build command: `npm run build`
   - Publish directory: `Frontend/dist`

3. **Deploy**
   - Click "Deploy site"
   - Netlify will automatically build and deploy

### CI/CD Pipeline

- Every push to `main` triggers automatic deployment
- Pull requests get deploy previews
- Build status shown in GitHub

### Configuration Files

| File | Purpose |
|------|---------|
| `netlify.toml` | Build configuration, redirects, headers |
| `public/_redirects` | SPA routing fallback |

## 📄 License

MIT License - Free to use for the JKKNIU MUN Club
