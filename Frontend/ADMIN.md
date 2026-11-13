# MUNC administration and no-code form builder

Existing public React Router routes and Layout remain intact. `/admin/*` is a separate, lazy-loaded administration workspace with the existing navy/gold branding and Inter/Poppins fonts. No large UI framework, deployed backend hostname, production mocks or browser token storage was added.

## Local use

Start the existing Django backend first, with a configured private `.env`:

```bash
cd Backend
source .venv/bin/activate
DEBUG=True python manage.py migrate
DEBUG=True python manage.py createsuperuser
DEBUG=True python manage.py runserver
```

Create the superuser only if you do not already have one. Enter its password interactively. In another terminal, from the repository root:

```bash
cd Frontend
npm ci
cp .env.example .env.local
npm run dev
```

Open `http://localhost:5173/admin/` and sign in. The example uses `http://localhost:8000/api`. Keep **localhost on both ports**, not a mix of localhost/127.0.0.1, for local session cookies. The backend must allow/trust that exact frontend origin; development defaults already include localhost:5173. Vite must be restarted after changing environment variables.

Production reads `VITE_API_BASE_URL` at build time and defaults to `/api`. Use the existing [same-origin Netlify proxy guide](../Backend/AUTHENTICATION.md) and [reviewable proxy example](../Backend/deployment/netlify-api-proxy.example.txt). Active Netlify configuration was not changed and nothing was deployed. Without a working proxy, configure an explicit backend API base including `/api`; cross-site production cookies require the backend's explicit HTTPS mode and browser support as documented there. Never put Django/Cloudinary/Redis credentials or session secrets in VITE variables; they are public build configuration.

## Routes and roles

| Route | Purpose |
| --- | --- |
| `/admin/login` | Secure administrator sign-in |
| `/admin` | Real scoped event/form overview |
| `/admin/events` | Assigned event list and search |
| `/admin/events/new` | Create an event, Super Admin only |
| `/admin/events/:id` | Edit assigned events; read-only for Reviewers |
| `/admin/forms` | Scoped form list, event/status filters and creation |
| `/admin/forms/:id` | Visual builder, preview and lifecycle actions |
| `/admin/submissions` | Filtered, paginated applications and CSV/XLSX exports |
| `/admin/submissions/:id` | Submitted answers, private documents, decisions, notes and review history |
| `/admin/sheets` | Choose a separate response sheet per form |
| `/admin/sheets/:formId` | All dynamic answer columns and protected image previews |

Super Admin and Event Admin roles can manage forms within their backend-authorized scope. Reviewers can see their assigned event context but cannot enter form-management routes. Application review is available at `/admin/submissions`, with Django Admin retained as a fallback. See [review API and security documentation](../Backend/REVIEW_API.md). The backend remains authoritative: route protection never replaces Django role/assignment checks.

Public pages never initialize an administrator session request. Existing historical event data, descriptions, image paths, Navbar/Footer and public routes are preserved. New backend events and registration forms do not replace the historical archive.

## Builder behavior

Select an event in Registration forms → Create form. Set a unique slug and any custom form type, then add questions visually. Supported types match the database engine: short/long text, email, phone, integer/decimal, date, dropdown, radio, checkboxes, file upload, URL and consent.

Each question has a stable generated key. Labels/help/placeholders/required flags can be changed without changing its identity. Choice option values also remain stable while labels are edited. Question ordering uses accessible up/down buttons with live announcements; deletion requires confirmation. Removing a question affects only the working draft, preserving prior published snapshots and answers.

The builder exposes conditional validation/default controls without requiring JSON or code. File definitions are restricted to supported image/PDF extensions and at most 10 MiB; real upload/content validation remains on Django. Consent cannot be preaccepted through a default value. Capacity blank means unlimited. Opening/closing times are explicitly Asia/Dhaka; requests carry the correct +06:00 offset.

Preview renders current unsaved questions and browser constraints. It never sends applicants' answers or files to the backend and clearly identifies itself as preview-only. Real submissions use the separate public registration pages described in [REGISTRATION.md](REGISTRATION.md). Published forms include an “Open published form” link.

Save draft sends complete question definitions, including their stable keys. It preserves the current published snapshot. Publish saves first, then calls the backend's publish action and reports the returned version only after success. Close and Duplicate also save the current draft first; duplicate creates a new independent draft and navigates to its builder. If a later action fails after the draft save succeeded, the UI states that partial outcome. No mutation is silently retried.

DRF validation errors are displayed in a focusable summary and at the affected metadata/question controls. Loading, empty, forbidden, missing-resource and disconnected API states are explicit. An HTML SPA fallback is rejected as an API-configuration error, never treated as success. Unsaved edits are guarded on in-app links, browser Back/Forward, reload/close and sign-out. Confirmation permits leaving without persisting the draft. Drafts are held in memory only, so confirmed navigation/refresh discards unsaved work.

The API adapter uses credentialed requests and an in-memory masked CSRF token, refreshes it after login, and validates that the browser retained the session. Session cookies are HttpOnly and managed by Django/browser. It does not use localStorage for credentials/tokens, follow supplied pagination hosts, or automatically replay failed writes. If a session expires while editing, server errors leave edits visible; signing out and back in requires acknowledging unsaved changes. Server permissions still apply on every request.

## Backend list extension

The existing `/api/admin/forms/` endpoint now supports GET as well as POST. GET uses the same Event Admin/Super Admin permission rules and assignment scope, includes drafts/closed forms, returns paginated metadata plus `field_count`, and accepts an optional numeric `event` filter. It does not return every form's full question schema. Existing per-ID details and mutation paths are unchanged. Backend tests verify that reviewers/unassigned users cannot use this list to obtain other events' definitions.

## Verification

```bash
npm run lint
npm run test
npm run build
npx playwright install chromium   # Once, if a local browser is not available.
npm run test:e2e
```

The four standard browser tests use explicit **test-only** request fixtures to cover forbidden roles, creation/editing/publication errors, close/duplicate, keyboard ordering, unsaved Back navigation, public-page isolation, and desktop/tablet/phone overflow checks. These fixtures are not imported by application code or included as backend behavior in production.

For a real Django integration test:

```bash
# From Frontend; requires Backend/.venv and its installed requirements.
python3 scripts/run-admin-integration.py
```

The runner creates a disposable database and random test credentials in a temporary environment, migrates it, seeds one fictional future event and two published editable example forms, starts a temporary Django server, runs the browser workflow, and removes the database/account when finished. It never connects to your development/production database or stores credentials in source. It verifies real session/CSRF handling, form creation, a server validation error, edited questions/options, persistence across reload, preview, publishing/public schema, closing and duplication. A second workflow checks anonymous schema rendering, real private image uploads, loss of a committed response and safe retry returning the same reference, confirmation reload and browser storage privacy. Real screenshots are produced at 1440px and 375px widths; the standard suite also checks 768px. Files are under ignored `test-results/`.

To use installed Chrome rather than Playwright's bundled Chromium:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome npm run test:e2e
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome python3 scripts/run-admin-integration.py
```

Live Netlify/Heroku proxy-cookie forwarding and cross-site browser policies require actual deployment domains and remain separate integration checks. Nothing in these scripts deploys the website or provisions external infrastructure.

## Application review and lifecycle additions

The dashboard now shows database aggregates for assigned events, published forms, all submissions, new/under-review applications and approved/rejected applicants. Applications supports event/form/status filters, name/email/reference search and server pagination. Exports use the same active filters across all matching pages. The private detail screen uses immutable submitted question labels/options, authorized document downloads and an append-only reviewer note/status timeline.

Form cards show submission counts and whether applications are currently accepted. Archive preserves all historical responses and schemas. Duplicate now permits selecting another authorized event; cross-event copies clear old deadlines and always begin as unpublished drafts. The real Django integration suite also checks review roles, file/export delivery, private notes, lifecycle actions and responsive widths.

Per-form spreadsheet views, private image behavior and API contracts: [FORM_SHEETS.md](../Backend/FORM_SHEETS.md).

## Email management

Super Admins and assigned Event Admins can use `/admin/email` (also `/admin/email-campaigns`) for overview, campaigns, templates, scheduled notices, delivery history, failed/uncertain outcomes and per-event settings. Existing application detail pages show delivery/payment summaries and manager-only payment verification. Payments remain separate from application decisions and uploaded evidence. No credentials enter React or browser storage. Previewing or queueing does not imply delivery; a configured backend worker and authenticated delivery webhook are required.

See [EMAIL_SYSTEM.md](../Backend/EMAIL_SYSTEM.md) for APIs/tests and [DEPLOYMENT.md](../Backend/DEPLOYMENT.md) for exact Brevo/Heroku setup. No provider account, paid service or deployment was provisioned.
