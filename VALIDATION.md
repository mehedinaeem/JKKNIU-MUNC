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
