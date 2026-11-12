# Validation results

Executed locally with Python 3.14.4, Django 5.2.19 and SQLite. Temporary test-only environment values were supplied; no `.env` or production secrets were generated.

- `pip check`: passed.
- `manage.py check`: passed, no issues.
- `manage.py makemigrations --check --dry-run`: passed, no model changes.
- `manage.py migrate --noinput`: passed, all built-in initial migrations applied.
- `manage.py test --verbosity 2`: all 23 tests passed (including Part 2 event/form coverage).
- `manage.py collectstatic --noinput`: passed, 154 files copied and 444 post-processed.
- `manage.py check --deploy`: no errors; advisory W005 and W021 remain because HSTS subdomains and preload require domain-wide confirmation. They are intentionally disabled and not silenced.
- `git diff --check`: passed.

The first test run warned that the static output directory did not exist; the subsequent successful `collectstatic` created it. Generated SQLite/static files and the virtual environment are ignored.

Not executed: live PostgreSQL migrations/integration, Heroku build/release/runtime integration, production-domain browser integration. No infrastructure or real credentials were provided, and deployment was explicitly excluded. PostgreSQL URL parsing is covered by an isolated test without a database connection. Frontend files were not modified; its build was not run because the prebuild script writes the gallery manifest.

## Part 2: event management

- Generated and applied `events/0001_initial` and `club_forms/0001_initial` on local SQLite.
- Re-ran Django system checks: no issues.
- Re-ran migration drift check: no changes detected; subsequent migration run had no pending migrations.
- Full suite: 23 tests passed, including all Part 1 tests.
- Added coverage for public published-only list/detail, staff writes, unauthorized/inactive users, CSRF, pagination, filters/search/order, duplicate slugs, date windows including PATCH, invalid inputs, custom multi-form types, cascade deletion, database constraints and the demo command.
- Executed `seed_demo_events` locally: one fictional published event and four draft example forms. Idempotency and production rejection are also tested.
- No frontend files modified, no historical archive imports, and no deployment performed.
- Live PostgreSQL and Heroku integration remain unexecuted; no infrastructure was provided.

## Part 3: dynamic form engine

- Applied `club_forms/0002` plus `registrations/0001` and `0002` locally.
- Django system checks: no issues. Migration drift check: no changes detected. No pending migrations after application.
- Full suite: **43 tests passed**, including all earlier tests and 20 dynamic-form tests.
- Tested all supported answer types, required and optional values, choice validation, unknown answers, defaults, file constraints, private-file permissions, duplicate field keys, incomplete nested PATCH input, staff/CSRF protection, unpublished/closed forms, deadlines, capacity and repeated submissions.
- Confirmed draft changes do not alter prior published schemas or stored answers; old-version submissions remain linked to their original snapshot. Model/queryset version mutations are rejected.
- Confirmed duplicate forms are independent drafts without copied versions/submissions.
- Confirmed local private upload/download and production rejection of filesystem uploads. Tests use temporary storage, not committed uploads.
- Frontend files were not modified during this work, and nothing was deployed.
- Not executed: live PostgreSQL concurrency testing, external durable private-storage integration, or Heroku integration. These require unavailable infrastructure. Local database tests use SQLite; production submission concurrency relies on PostgreSQL row locking and conditional counter updates.

## Part 4: public submissions and secure files

- Applied `registrations/0003`, `0004`, and `0005` locally, including the data-preserving submission rename/backfill, public references, review state, file metadata, status audit and cleanup intent tables.
- System checks passed; migration drift check reported no changes; no pending migrations remain.
- Full suite: **64 tests passed**. Existing tests retain authenticated-route coverage; additional cases cover anonymous receipt privacy, duplicate email normalization, version errors, form admission limits, MIME/content/file errors, image/PDF uploads, private access, status authorization/auditing and CSRF, submission quotas, payload limits, provider calls and cleanup retries.
- A real SQLite transaction test forces a commit failure after a mocked successful upload and verifies rollback of submission/files/capacity plus compensating provider deletion.
- Migration test creates an old-format submission/file/version, migrates forward, and verifies preserved ID, answers, timestamps, version/file links and backfilled contact/reference/event/form data.
- Cloudinary SDK calls are mocked, with authenticated/raw upload parameters asserted. Signed downloads are fetched server-side; tests confirm no provider redirect/public file URL or applicant data in public receipts.
- Failed cleanup is retained as a retryable intent; the cleanup command is tested, including protection for committed assets.
- `pip check`: no broken requirements. `git diff --check`: passed.
- `check --deploy` with synthetic nonsecret Cloudinary/Redis/PostgreSQL configuration had no errors. The two earlier HSTS advisory warnings (W005/W021) remain intentional. This verifies configuration shape, not provider credentials or network connectivity.
- Not executed: live Cloudinary uploads/private delivery, actual shared Redis integration, PostgreSQL concurrent submission testing, or Heroku deployment/runtime checks. No real infrastructure/credentials were supplied, and nothing was deployed.
- Frontend files and archive content were not changed during this work. Existing unrelated frontend/Netlify edits were preserved.

## Part 5: administrator sessions and event-scoped roles

- Applied `accounts/0001_initial` (unique user/event assignments). Managed Django role groups/permissions synchronize after migrations; the explicit setup command is idempotent and does not assign users or create credentials.
- System checks passed; no migration drift or pending migrations. `git diff --check` passed.
- Full suite: **88 tests passed**, including all earlier event/form/submission checks plus administrator authentication/authorization coverage.
- Tested Super Admin (native superuser and group), Event Admin and Reviewer access; plain staff/direct permissions without a role are denied. Verified unassigned event/form/application IDs cannot bypass scope, assignment/role revocation takes effect, and private providers are not called for unauthorized downloads.
- Fallback Django Admin lists, object pages and related choices are scoped. User/group/assignment administration remains Super Admin-only. API and fallback status changes retain actor audits.
- Tested anonymous CSRF bootstrap, CSRF-required login/logout, trusted/untrusted Origin handling, generic bad/inactive/nonadministrator credential failures, session/CSRF rotation, session logout, disabled accounts, current-user responses, and login limits for both API and fallback admin.
- Tested production proxy-mode secure/Lax/HttpOnly cookie settings and explicit cross-site None/Secure settings. Invalid HTTP, wildcard or untrusted cross-site configurations fail startup.
- Production `check --deploy` with synthetic nonsecret infrastructure configuration reported no errors; prior HSTS W005/W021 advisories remain intentional. No real infrastructure connectivity was implied by that check.
- No users, passwords, production secrets, frontend pages/styles or active Netlify routing changes were created by this task. A deployment-only Netlify proxy example and secure first-superuser instructions are documented in AUTHENTICATION.md.
- Not executed: real Netlify/Heroku proxy cookie forwarding, browser third-party-cookie policies, or live shared Redis/PostgreSQL integration. Those require deployment domains/infrastructure. Nothing was deployed.

## Part 6: React administration and no-code form builder

- Added the separate lazy-loaded React `/admin/*` workspace without modifying public route definitions, Layout, historical event data/descriptions, image paths or existing public pages.
- Added scoped GET support to the existing `/api/admin/forms/` endpoint, returning paginated metadata and field counts with an optional event filter. Existing create/edit/publish permissions and mutation paths remain intact; no model migration was needed.
- Django system checks and migration drift check passed. Full backend suite: **89 tests passed**, including the new draft-list authorization check.
- Frontend `npm run lint`: passed with no errors/warnings. `npm run test`: **10 tests passed**. `npm run build`: passed with a separate lazy admin JS/CSS chunk.
- Standard Playwright suite: **4 tests passed**, covering login/role guards, form creation/editing, server errors, publication, closing, duplication, keyboard ordering, unsaved Back/link warnings, public-page isolation and horizontal-overflow checks at 375/768/1440px.
- Real Django browser integration: **1 complete workflow passed** against an isolated temporary SQLite database with disposable credentials. Verified genuine session/CSRF requests, creation, server-side field errors, question/option editing, description/date/capacity persistence across reload, preview, publication/public schema, closing and duplication.
- Visually inspected desktop and phone screenshots of the real backend workflow. Owned test servers stopped and temporary test databases/accounts were removed; development data was not used for the integration test.
- Compatible dependency security updates were applied; npm reported zero known vulnerabilities after the update. No large UI framework or permanent backend mocks were added.
- Live Netlify/Heroku proxy/cookie forwarding remains an external deployment check. No deployment, production credentials, public archive imports or active Netlify routing changes were performed.
- Frontend setup, route map, API behavior and reproducible test commands are documented in Frontend/ADMIN.md.

## Final integrated verification: administration and public registration

- Rechecked all requested admin pages, session route guards, schema editing/preview/lifecycle actions and unsaved navigation after adding public registration.
- Full backend suite: **94 passed**. System checks, migration drift check and local migrations passed; migration `0006` adds nullable per-attempt idempotency metadata without replacing existing responses.
- Frontend lint and production build passed. **20 frontend tests**, **4 standard browser tests**, and **2 real Django browser workflows** passed.
- Real workflows use an isolated temporary SQLite database and test accounts, with local private uploads inside the temporary directory. Both editable seed templates are instantiated/published only in that disposable test database.
- Public workflow checks schema-driven categories/questions, actual PNG photo/receipt uploads, a deliberately lost successful receipt, explicit retry returning the original reference, confirmation reload and absence of applicant contact data in sessionStorage. Backend tests verify no extra submission or upload is created by replay.
- Desktop/phone screenshots were generated; admin screenshots were visually inspected. Existing archive definitions and existing public routes/layout remain intact.
- Cloudinary, deployed Netlify/Heroku cookie forwarding, PostgreSQL concurrency and live infrastructure remain unexecuted external checks. No deployment was performed. See Frontend/ADMIN.md and Frontend/REGISTRATION.md for reproducible local commands.

## Event administration and application review

- Added server-scoped dashboard totals, searchable/paginated application lists, private submitted-answer detail, append-only reviewer notes, existing status audits in the review timeline, and protected CSV/XLSX exports.
- Migration `registrations/0007` creates reviewer notes and export/file-access audit logs. Applied locally; system check and migration drift check passed.
- Role tests cover Super Admin, Event Admin, assigned Reviewer, anonymous/plain staff, revoked assignments, other-event ID/filter attempts, CSRF writes, notes author spoofing, version-specific exports, formula escaping, export bounds, filtered pagination and Bangla-name search on SQLite.
- Full backend suite: **103 tests passed**. Frontend lint, production build and **24 tests passed**.
- Existing browser regression suite: **4 passed**. Real Django integration suite: **3 passed**, including application search, reviewer notes/status persistence, both export downloads, private attachments and denied access to another event. Builder integration additionally checks safe archive and cross-event duplication with cleared deadlines.
- Browser integration uses disposable SQLite/accounts/private files only. Review screenshots checked at desktop/tablet/phone widths; phone screenshot visually inspected. Corrected cross-origin `Content-Disposition` exposure for authenticated blob downloads.
- Existing public pages, archive and styling remain intact. No deployed infrastructure or active Netlify routing was changed. Live Cloudinary, Heroku/Netlify proxy-cookie delivery and PostgreSQL concurrency remain external checks; nothing was deployed.
- API contracts, export limits, audit semantics and local commands: REVIEW_API.md. React reviewer routes: `/admin/submissions` and `/admin/submissions/:id`.

## Public event catalog integration and complete workflow

- Combined published API events with the static archive using conservative slug/title-date deduplication; retained historical detail markup/data/images and backend-independent galleries. Added backend event details and registration entry points using server-computed availability.
- Verification report: INTEGRATION_VERIFICATION.md. Django checks/migration checks passed, **104 backend tests**, **30 frontend tests**, **4 browser regressions** and **5 real Django browser workflows** passed. Lint and production build passed.
- Continuous National MUN workflow creates/publishes an event and editable multi-category form through admin UI, submits a required photo anonymously, verifies saved private file references through a real download, approves the applicant and exports CSV/XLSX. Negative cases cover deadlines, invalid uploads, missing answers, unauthorized access and duplicate applications.
- All **38 historical detail URLs/descriptions** and **190 referenced image paths** checked; gallery keyboard controls and API outage fallback verified. No deployment or automatic archive import performed. Live Cloudinary, proxy-cookie forwarding and PostgreSQL concurrency remain external checks.

## Homepage upcoming events and automatic past-event placement

- Added a shared upcoming-events section immediately below the homepage hero (nearest three events), plus Upcoming events and Past events sections on the Events page. Existing search filters, historical records, detail URLs and galleries remain intact.
- Published backend events remain upcoming/ongoing until their end timestamp, or start timestamp if no end is provided. Registration closure hides registration links without prematurely archiving a future event. A local boundary timer and focus/visibility checks update open pages automatically.
- Added timestamp-boundary, ongoing-event, registration-deadline and in-place rollover tests. Frontend checks: **33 tests passed**, lint/build passed; **4 browser regressions passed**. Existing real Django integration was extended to check homepage registration links, upcoming/past sections, date rollover and phone/tablet/desktop layout. Tests now use a fixed API base in Vitest so a developer's `.env.local` does not change unit-test expectations.
- No deployment, database scheduler, production account changes or historical content edits were performed. Admins control visibility by publishing a future-dated event and its registration form.

## Separate response sheets with private images

- Added `/admin/sheets` and `/admin/sheets/:formId`, linked from the sidebar, forms and filtered applications. Each form has its own paginated sheet with all published question keys, metadata, search/status filters and text exports. Historical labels, options and field types come from each submitted version; removed question columns remain available.
- Added scoped GET `/api/admin/forms/{id}/sheet/` and protected image previews at `/api/submission-files/{id}/preview/`. Images are bounded, decoded/re-encoded without metadata, private/no-store, event-authorized and audited. Thumbnail/large previews stay server-mediated; original files remain protected downloads. Browser blobs are revoked and requests aborted on cleanup.
- Django checks and migration drift check passed; no new schema migration or dependency required. **109 backend tests** and **39 frontend tests** passed, plus frontend lint/build and **4 browser regression tests**. The **5 real Django workflows** include sheet row/column display, actual image loading/enlargement, separate form switching and responsive scrolling at 375/768/1440px.
- Visually inspected desktop and mobile sheet screenshots. No public applicant endpoint or storage-provider URL was introduced. No deployment was performed. Cloudinary remains mocked in backend storage tests; browser previews use real temporary private files.
- Usage/API/security documentation: FORM_SHEETS.md.
