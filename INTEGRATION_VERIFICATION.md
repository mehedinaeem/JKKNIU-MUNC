# Frontend/backend integration verification

Verified locally on 12 November 2026. Nothing was deployed. React remains the Netlify frontend; Django remains an independent backend intended for Heroku.

## Implemented integration

`/events` immediately renders the historical archive and asynchronously adds all published backend events through the configured API adapter. Search, year/category filters, counts and date sorting use the merged collection. Public reads never initialize an administrator session.

Deduplication gives historical records priority by exact slug, or normalized title plus the same **precise calendar date** in Asia/Dhaka. API-only duplicates follow the same identities. Historical titles, descriptions, slugs, images, galleries and detail markup are retained. The code does not guess identity from a title/year alone: recurring events and imprecise archive dates must not be accidentally collapsed. Use the existing historical slug when publishing an overlapping record. A distinct API alias with an exact title/date match redirects its detail page to the original historical URL.

New API events use the existing `/events/:slug` route and branded event styles. Registration links lead to `/events/:slug/register`, where applicants choose among published categories. Forms and submissions continue to use the immutable published schema and server-side admission checks.

Public event responses now include read-only `registration_open`, computed from published form versions, event/form deadlines, capacity and status. Availability queries prefetch only form metadata and version identifiers; they do not load every version's answer schema. Event details separately refresh form availability before showing the registration action. Django still rechecks every rule at submission time.

An unavailable API does not block or remove historical events. The catalog shows a retry notice while the complete archive remains usable. Historical detail pages and galleries require no backend response. A missing API event and a temporary API failure have different messages and a route back to the archive. New event pages distinguish unavailable registration data from closed registration.

## Verification results

| Check | Result |
| --- | --- |
| Django system check | Passed |
| Migration drift check / local migrations | Passed; no new migration required for this catalog integration |
| Complete Django suite | 104 passed |
| Frontend lint | Passed |
| Frontend tests | 30 passed |
| Production build | Passed |
| Existing Playwright regression suite | 4 passed |
| Real Django browser integration | 5 passed |
| Historical records | All 38 existing detail URLs and editorial descriptions checked |
| Historical assets | All 190 referenced cover/card/gallery paths exist |
| Gallery interaction | Open, keyboard next and Escape close checked |
| Responsive layouts | Horizontal overflow checked at 375, 768 and 1440 pixels; screenshots generated |

### Continuous National MUN workflow

`Frontend/e2e/integration-live.spec.js` creates a National MUN conference through the actual administrator UI, sets its registration window, creates a Delegate form, adds required name/email/file questions, saves and publishes the schema, and creates/publishes a second application category.

A separate anonymous browser context then discovers the new event in `/events`, opens its detail page, follows registration, chooses Delegate rather than Executive Board, uploads a real PNG and submits. It receives the reference returned by Django. The administrator opens that exact application, checks saved answers/file metadata, downloads the stored private image and verifies its PNG signature, approves the application, checks the persisted status audit, and downloads both CSV and XLSX exports. The CSV contains the same reference. Public receipt JSON contains only the reference and success message.

The same test checks missing required answers, invalid HTML upload rejection, denied anonymous admin/file access, duplicate application rejection and a single persisted submission. After the administrator moves the event deadline into the past, Django rejects another submission and the event page removes its registration action and displays the closed message.

### Additional coverage

- `archive-live.spec.js` deliberately aborts API requests and checks all historical detail URLs, original editorial descriptions, cover references and gallery counts; it also exercises the gallery keyboard controls and the unknown-event network-error state.
- Catalog tests cover slug overlap, exact title/date overlap, duplicate API rows, preservation of original objects, Dhaka date boundaries, draft exclusion, safe image URL protocols, alias redirection and API outage fallback.
- Existing real integration tests cover draft validation, persistence, publication, close/archive, duplication across events, upload retry after a lost committed receipt, confirmation reload, private reviewer notes, exports, assigned-event authorization and mobile review/builder layouts.
- Django tests cover required answers, file content/type limits, deadlines, duplicates, transaction-safe capacity admission, private storage cleanup/error paths, staff role scope and CSRF. Availability tests verify that draft/unpublished, future-opening, expired, archived and full forms do not advertise open registration.

Tests use a temporary SQLite database, disposable accounts and temporary private upload storage. Production data and development accounts are not used. Submission rate limits are increased **only in the isolated browser settings** so negative cases run together; the production limits and their backend tests remain intact. Browser fixtures exist only in the separate regression suite; the full National MUN workflow uses actual Django APIs without mocked success responses.

## Reproduce

From `Backend/`, using its installed virtual environment:

```bash
DEBUG=True .venv/bin/python manage.py check
DEBUG=True .venv/bin/python manage.py makemigrations --check --dry-run
DEBUG=True .venv/bin/python manage.py migrate --noinput
DEBUG=True .venv/bin/python manage.py test --noinput
```

From `Frontend/`:

```bash
npm run lint
npm run test
npm run build
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome npm run test:e2e
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome python3 scripts/run-admin-integration.py
```

Omit the browser executable environment variable if Playwright Chromium is installed. The integration runner owns and stops its local Django/Vite processes and removes temporary test accounts/database/files. Browser screenshots and traces are written under ignored `Frontend/test-results/`.

For normal development, start `DEBUG=True python manage.py runserver` from the activated backend environment and `npm run dev` from `Frontend/`. Set `VITE_API_BASE_URL=http://localhost:8000/api` in the private frontend environment, using localhost consistently on both ports. Backend `.env` must contain your local `SECRET_KEY`; no production key is generated. The first staff account is created interactively with `DEBUG=True python manage.py createsuperuser` if one does not already exist. See [ADMIN.md](../Frontend/ADMIN.md) for full setup.

## Remaining external checks

Live Netlify/Heroku routing and cookie forwarding, actual Cloudinary connectivity/retention, and PostgreSQL concurrency require the real infrastructure and were not executed. Cloudinary SDK behavior is covered with backend test doubles; the browser suite uses real temporary private storage. The recommended production API base remains `/api` behind the documented same-origin Netlify proxy, or an explicitly configured HTTPS API base with the documented credentialed-cookie settings. No Heroku hostname is hardcoded, no frontend is moved to Heroku, and no deployment or paid infrastructure is provisioned.
