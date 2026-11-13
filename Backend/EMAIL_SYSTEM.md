# Email management implementation and verification

The existing repository had applicant emails, immutable form versions, application-status audits and private uploaded files, but no email service/queue or independent payment-verification ledger. The new `mailing` app extends those existing records through foreign keys and post-commit hooks. It does not duplicate registration records, change public event/archive content or use a separate authentication system.

## Features and routes

Open `/admin/email` in the React administration workspace. `/admin/email-campaigns` redirects to the Campaigns list.

- Overview: scoped queued, pending, provider-accepted, confirmed-delivered, failed and uncertain counts; approximate global daily budget and last worker activity.
- Campaigns: assigned event, dynamically loaded form/type groups (including Delegate/Executive Board/custom), status/payment/custom-applicant filters, unique eligible count, subject, rich formatting, plain text, personalized sandbox preview, administrator-only test queue, draft/save, confirmed send/schedule, pause/resume/cancel and progress refresh.
- Templates: seeded defaults plus event overrides, approved placeholder validation, safe HTML/plain text and previews. Event Admins cannot edit global defaults; they can customize a copy for an assigned event.
- Scheduled: pending scheduled campaign list.
- Delivery history / failed and uncertain: paginated event/status filters, provider ID, attempt history, known-failure retry and manual reconciliation of unknown outcomes. Acceptance never means delivery.
- Settings: provider readiness without secrets, quota/retention information, per-event automatic notification toggles and instructions, and explicit optional-communication consent/evidence recording.
- Existing applicant detail: separate payment-verification controls for managers, and scoped recent email/payment summaries for reviewers. Uploading a receipt, entering a transaction ID or approving an application never verifies payment automatically.

Conference reminders and Executive Board interview invitations are editable templates used with the same scheduled campaign workflow, rather than a second hardcoded reminder/registration system. Categories and recipients derive from database forms and registrations. A campaign sends one message per normalized address; where multiple selected applications share an address, its earliest selected application supplies personalization. Question labels/keys are used only to find a likely applicant name; unmatched custom labels fall back to “Applicant”, not a guessed institution name.

## Queue and safety

The transport uses Brevo HTTPS REST, configurable connect/read timeouts and a provider abstraction returning sanitized outcomes. Registration, status and verified-payment hooks call only after database commit. They never contact Brevo. Queue insertion errors are caught; an enabled worker reconciles missing jobs from committed authoritative records. `EmailSystemState` records a migration-time cutover so existing earlier registrations do not unexpectedly receive old confirmations.

Automatic confirmations use one unique event key per submission; each meaningful status or payment transition has its own audit-ID key. Campaign jobs have a fixed per-campaign recipient snapshot, unique normalized recipient constraint and opaque hashed keys. Content, sender and headers are frozen for request retries. New edits cannot change previously queued content. Pausing/cancelling excludes unclaimed messages; in-flight requests may finish.

PostgreSQL row locking, a shared daily quota/rate row, atomic claims and attempt counters support multiple workers. Transactional jobs precede campaigns and administrator tests. Bulk/test jobs cannot consume the configurable reserved capacity. Pending jobs survive quota exhaustion and continue on the next configured quota day. Definite retryable failures back off; timeouts with possible acceptance, ambiguous provider errors and expired claims stay unknown and are not automatically resent. A database failure after provider acceptance leaves a durable in-flight row that becomes uncertain, rather than a duplicate request. The provider idempotency window is finite; this system does not claim mathematically guaranteed exactly-once external delivery.

A verified bearer-authenticated webhook records acceptance/delivery/deferral/bounce/failure without storing raw applicant payloads. Duplicate and out-of-order events are handled. Hard/invalid/spam/blocked addresses are suppressed. Optional marketing requires explicit evidence-backed consent, includes a signed opaque opt-out link, and is checked again before send. The opt-out endpoint cannot subscribe anyone or retrieve applicant data. Normal data-processing consent is not automatically treated as marketing consent.

No attachment, private Cloudinary URL or recipient list enters outgoing messages. HTML is allowlisted, variables escaped, and there is no Django template execution/eval. Staff APIs retain Django sessions, CSRF, rate limits and event assignments. Existing ReviewAccessLog records administrator actions; payment changes and delivery attempts have separate immutable operational audit records. Terminal message content can be redacted while retaining idempotency tombstones and minimal suppression/consent records.

## Backend file manifest

New files under `Backend/mailing/`:

| File | Purpose |
| --- | --- |
| `apps.py`, `signals.py` | App registration and safe post-commit integration |
| `models.py` | Templates, campaigns, messages, attempts, preferences, event settings, payment/audit records, quotas, cutover and webhook deduplication |
| `defaults.py` | Editable default template definitions |
| `rendering.py` | Strict placeholder renderer and HTML sanitizer |
| `notifications.py` | Automatic contexts, unique jobs and missed-hook reconciliation |
| `providers.py` | Brevo transport and sanitized result parsing |
| `campaigns.py` | Eligibility, deduplication, snapshots and unsubscribe capabilities |
| `queue.py` | Claims, quotas, priority, leases, backoff, outcomes and progress |
| `permissions.py`, `serializers.py`, `views.py`, `urls.py` | Scoped administrative API |
| `webhooks.py` | Authenticated delivery events and opt-out endpoint |
| `admin.py` | Super Admin read-only audit fallback |
| `management/commands/process_email_queue.py` | Bounded queue batches / dry run / transactional-only |
| `management/commands/email_worker.py` | Optional continuous worker |
| `management/commands/purge_email_history.py` | Configurable terminal-message content redaction |
| `tests.py` | Mocked transport, transaction, privacy, authorization and concurrency coverage |

Modified backend files: `config/settings.py`, `config/urls.py`, `.env.example`, `Procfile`, `README.md`, `VALIDATION.md`. Added deployment/verification documents: `DEPLOYMENT.md` and this file. No new Python dependency was required; requests, Django and DRF were already installed. No existing user/registration model was replaced.

## Migrations

Run ordinary `python manage.py migrate`:

1. `mailing/0001_initial`: new durable email/settings/payment/audit models, indexes and constraints.
2. `mailing/0002_seed_email_defaults`: 11 editable global templates and the notification cutover; existing content is not overwritten.
3. `mailing/0003_remove_emailmessage_mail_campaign_unique_recipient_and_more`: preserves recipient uniqueness while allowing blank redacted tombstones.
4. `mailing/0004_emailmessage_extra_headers`: frozen delivery headers, including consent-based unsubscribe capabilities, for identical retry payloads.

All four were applied to the local database. Existing historical events and earlier registration content were not imported or overwritten.

## Frontend file manifest

New `Frontend/src/pages/admin/email/` files:

- `EmailApp.jsx`: scoped module navigation, overview, campaigns/scheduled list and delivery/failed history.
- `CampaignEditorPage.jsx`: draft composition, selection/count, preview, test queue and lifecycle confirmations.
- `TemplatesPage.jsx`: safe editable event/global templates.
- `EmailSettingsPage.jsx`: readiness, event notification settings and optional-consent records.
- `EmailUI.jsx`, `useEmailPreview.jsx`: formatted editor and sandbox preview helpers.
- `email.test.jsx`: acceptance-versus-delivery, disabled transport and preview/editor safety checks.

New `Frontend/src/components/admin/SubmissionEmailPanel.jsx`; modified `pages/admin/AdminApp.jsx`, `pages/admin/ApplicationDetailPage.jsx`, `components/admin/AdminLayout.jsx`, `components/admin/AdminUI.jsx`. Integration runner/config and `e2e/email-live.spec.js` exercise the actual API with transport disabled. No frontend credentials, large UI framework, permanent mock provider or active Netlify routing change was added.

## API contract

All `/api/admin/email/` management endpoints require Super Admin or assigned Event Admin privileges. GET submission summaries additionally permit assigned Reviewers. All mutations use existing session CSRF protection. Lists are paginated, and no public endpoint exposes a recipient list.

| Method and path | Purpose |
| --- | --- |
| GET `/api/admin/email/overview/` | Counts, quota estimate and worker/readiness state |
| GET `/api/admin/email/configuration/` | Nonsecret configuration and allowed variables |
| GET, POST `/api/admin/email/templates/` | List/create global or event templates |
| GET, PATCH `/api/admin/email/templates/{id}/` | Read/update an authorized template |
| POST `/api/admin/email/templates/preview/` | Sanitized example rendering |
| GET, POST `/api/admin/email/campaigns/` | List/create draft campaigns |
| GET, PATCH `/api/admin/email/campaigns/{id}/` | Read/update an unfrozen draft |
| POST `/api/admin/email/campaigns/{id}/preview/` | Eligibility count and personalized preview |
| POST `/api/admin/email/campaigns/{id}/test/` | Queue only to the logged-in admin; UUID `request_key` required |
| POST `/api/admin/email/campaigns/{id}/send/` | `{"confirm":true}` marks ready for a background snapshot |
| POST `/api/admin/email/campaigns/{id}/schedule/` | `{"confirm":true,"scheduled_at":"2027-01-01T09:00:00+06:00"}` |
| POST `/api/admin/email/campaigns/{id}/pause/`, `resume/`, `cancel/` | Control unclaimed work |
| POST `/api/admin/email/recipients/` | Validate filters and count unique currently eligible recipients |
| GET `/api/admin/email/recipient-options/?event={id}&search=...` | Scoped paginated custom-applicant picker |
| GET `/api/admin/email/messages/` | Event/status/campaign/submission filters; `attention=1` for failed/uncertain states |
| POST `/api/admin/email/messages/{uuid}/retry/` | Confirmed known-failure retry; never accepted/uncertain sends |
| POST `/api/admin/email/messages/{uuid}/resolve/` | Audited original outcome, accepted provider ID or cancellation; no resend |
| GET, PATCH `/api/admin/email/settings/{event_id}/` | Per-event toggles and next instructions |
| POST `/api/admin/email/preferences/` | Record explicit consent/withdrawal for an assigned application with evidence |
| GET `/api/admin/email/submissions/{uuid}/` | Scoped payment and recent email summary |
| PATCH `/api/admin/email/payments/{uuid}/` | Manager-only independent payment decision and audit |
| POST `/api/webhooks/brevo/` | Bearer-authenticated, bounded, idempotent provider events |
| GET, POST `/api/email/unsubscribe/?token=...` | Signed capability confirmation / optional opt-out only |

Recipient filters allow `form_ids`, actual custom `form_types`, application `statuses`, `payment_status` (`unpaid` means not verified, or `verified`) and validated custom `submission_ids`. Custom selection explicitly requires at least one selected applicant; an empty custom list cannot accidentally mean everyone. Every referenced form/submission must belong to the selected authorized event. The snapshot happens in the worker when actual sending starts, including scheduled jobs, rather than during an HTTP request.

## Local test commands and results

```bash
cd Backend
DEBUG=True .venv/bin/python manage.py check
DEBUG=True .venv/bin/python manage.py makemigrations --check --dry-run
DEBUG=True .venv/bin/python manage.py migrate --noinput
DEBUG=True .venv/bin/python manage.py test --noinput
DEBUG=True .venv/bin/python manage.py process_email_queue --limit 25 --dry-run
```

```bash
cd Frontend
npm run lint
npm run test
npm run build
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome npm run test:e2e
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome python3 scripts/run-admin-integration.py
```

Validation report for this change:

- Django system check and migration drift check passed.
- Complete Django suite: **135 tests run; 134 passed, 1 skipped**. The conditional PostgreSQL parallel-claim test cannot execute because PostgreSQL is not installed/configured in this local SQLite environment. A PostgreSQL-specific test is supplied and must be executed against a dedicated test database before multiworker production scaling.
- React lint and production build passed. **42 frontend tests passed**.
- Existing browser regression suite: **4 passed**. Real Django workflows: **6 passed**, including email admin draft/count/preview, administrator-only queued test, scheduling, pause/resume/cancellation, template preview and responsive widths, plus full registration/review/upload/export/archive regressions.
- Email-specific coverage includes delegate/EB/custom confirmations, meaningful approval notifications, separate verified-payment emails and permissions, normalized bulk deduplication, recipient filters, snapshots, quota/reserve/next-day behavior, retry/backoff bounds, unknown outcomes, provider failure sanitization, authenticated duplicate/out-of-order webhooks, suppression, unsubscribe/consent, callback reconciliation, database rollback and failures after provider acceptance, template overrides, frozen request headers, retention and read-only dry runs.
- Browser email transport is explicitly disabled and providers are mocked in unit tests; no real email or production credential was used. Temporary browser databases/accounts/files are removed. Desktop/tablet/phone screenshots are under ignored test-results/.

Remaining manual work: Brevo account/plan and transactional activation, sender/DNS verification, real server config vars/secrets, webhook creation, deliberate staging send/inbox/header/delivery checks, dedicated PostgreSQL concurrency verification, and a funded Scheduler/worker choice. No live email delivery, DNS change, infrastructure provisioning, paid dyno scaling or deployment was executed. Exact environment variables, Heroku commands, sender/DNS/webhook setup, costs, monitoring and troubleshooting are in DEPLOYMENT.md.
