# Architecture inspection and backend boundaries

## Existing project

Inspected the repository structure and all frontend source/configuration/data text files before implementation. The project initially contained `Frontend/`, a root `netlify.toml`, and a minimal root README. There was no backend. Existing uncommitted edits to `Frontend/src/data/executiveCommittee.js` and `netlify.toml` were preserved.

`Frontend/package.json` defines React 19, React Router 7, Vite 7, Tailwind CSS 3, PostCSS, Autoprefixer and ESLint. `main.jsx` mounts `App.jsx` under React StrictMode. Vite uses the React plugin. Tailwind utilities, global CSS, and component-specific styles provide the design. `predev`/`prebuild` run `scripts/generate-gallery-manifest.mjs`, which fingerprints event gallery assets for deduplication. `public/` holds event images, committee portraits and SPA redirect configuration; `src/assets/` includes the hero video and logos.

`App.jsx` defines `/`, `/about`, `/events`, `/events/:slug`, `/gallery`, and `/contact`, nested under `Layout`. Netlify builds `Frontend/` with `npm run build` and publishes `dist`, with SPA fallback routing. All routes, designs, data, media paths and deployment configuration remain unchanged.

`events.js` exports the event archive, including stable IDs, slugs, supplied display dates (sometimes approximate or provisional), years, categories, status, descriptions, image paths, galleries and source links. `eventDescriptions.js` supplies longer narratives keyed by event ID. No import, rewrite, normalization or database copy of this content was performed.

`EventsPage.jsx` sorts the local archive using `newestFirst`, derives years/categories, and filters by search/year/category in memory. `EventDetailsPage.jsx` looks up a local slug, prefers the separate narrative, renders supplied detail fields and source links, and provides gallery and older/newer navigation. Unknown slugs have a local fallback. `gallery.js` builds a deduplicated gallery from the archive and generated manifest. Organization and committee content are also local modules. The contact form simulates submission in client state; it has no server persistence. No fetch/Axios API layer was found.

## Reusable frontend components

| Component | Reuse |
| --- | --- |
| `Layout`, `Navbar`, `Footer` | Shared application shell and navigation |
| `HeroVideo`, `ClubHistory` | Homepage media and organization history |
| `EventCard`, `EventFilters`, `EventsStats` | Archive display, filtering and counts |
| `EventImage` | Responsive archive images and fallback handling |
| `EventGallery`, `EventLightbox` | Event media browsing |
| `EventDialog` | Shared accessible modal used by event and gallery lightboxes |
| `GalleryTile`, `GalleryLightbox` | Deduplicated gallery presentation |
| `ExecutiveCommittee`, `LeadershipTier`, `ExecutiveMemberCard` | Committee hierarchy and profiles |
| `eventUtils.js` | Supplied date display and archive ordering |

These components can later consume compatible API data through a separate frontend adapter without changing their presentation contracts. Relative `/events/...` images currently belong to the Netlify origin, not the Django host; any future API integration must preserve that ownership and the original date precision.

## Backend

`config` owns environment settings, routing, WSGI/ASGI and health. Public health and event reads explicitly permit anonymous access; DRF otherwise defaults to authenticated access. `events` owns the Event model, serializers, query validation, staff permission class, public/staff views, routes and Django Admin integration. Simple CRUD uses DRF persistence hooks; the transactional sample-data command owns its multi-record operation, so no redundant service layer is needed yet.

`forms` owns RegistrationForm, its serializer and Django Admin. It retains the `club_forms` Django app label. An event has many forms through `registration_forms`; types are administrator-defined strings. Removing an event cascades to its forms. Forms are managed through Django Admin in this phase, with no public form API or submission processing. `accounts` and `registrations` remain foundations for future workflows.

Event organizers reference the configured user model and default to the creating staff member. Removing an organizer sets the reference to null without deleting the event. Event and form slugs are globally unique within their respective models. Cover images are external URL references, not uploads. Model clean methods, serializers (including PATCH merged-value validation) and database constraints enforce date-window order and positive-or-unlimited form capacity.

Only exact `published` event status is visible publicly; completed/cancelled/draft events return 404 even to staff on public endpoints. Explicit publishing controls visibility, independent of dates. Staff write routes support only the requested POST/PATCH/DELETE methods. Session authentication and CSRF protection remain enabled. Django Admin uses its standard per-model permissions; API writes require active authenticated staff.

The database contains new backend event records only. The explicit, debug-only demo command creates fictional development records without reading the historical archive, overwriting existing records or creating accounts. Netlify and Heroku remain independent, with no frontend modifications or deployment performed. See [EVENT_API.md](EVENT_API.md) for API contracts and examples.
