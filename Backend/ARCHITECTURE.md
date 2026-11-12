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

`forms` owns RegistrationForm, ordered FormField working drafts, immutable JSON FormVersion snapshots, schema/answer validation, transactional services, staff lifecycle APIs and public reads. The `club_forms` app label remains unchanged. Choices are embedded structured values within a field, so separate section/choice tables are unnecessary for this scope. `registrations` stores FormSubmission records tied to event/form/protected version, applicant email, public references, review state and private file metadata. It supports anonymous submissions plus the earlier authenticated route, staff review/status APIs and status audits. See [FORM_ENGINE.md](FORM_ENGINE.md) for contracts and safeguards.

The dynamic engine uses PostgreSQL row locks and atomic capacity increments. New private files use explicit temporary/Cloudinary provider adapters. Production filesystem writes are forbidden, authenticated Cloudinary credentials stay server-side, and shared Redis enforces submission quotas. Durable upload intents and a cleanup command compensate for remote/DB failures and crashes. No external infrastructure or credentials have been provisioned. The original storage alias remains only for reading historical files. Django Admin exposes drafts/lifecycle actions and read-only published versions/submissions. Historical responses are not rewritten by schema edits.

Event organizers reference the configured user model and default to the creating staff member. Removing an organizer sets the reference to null without deleting the event. Event and form slugs are globally unique within their respective models. Cover images remain external URL references. Event/form date-window validation is retained.

Only exact `published` event status is visible publicly; completed/cancelled/draft events return 404 even to staff on public endpoints. Event staff write routes retain POST/PATCH/DELETE; deletion is prevented if protected published form versions exist. Session authentication and CSRF protection remain enabled.

The database contains new backend event records only. The explicit, debug-only demo command creates fictional development records without reading the historical archive, overwriting existing records or creating accounts; its draft forms still require fields and explicit publishing. Netlify and Heroku remain independent, with no frontend modifications or deployment performed. See [EVENT_API.md](EVENT_API.md) for API contracts and examples.

See [SUBMISSIONS.md](SUBMISSIONS.md) for current public/private API boundaries, storage, rate limits and cleanup operations.
