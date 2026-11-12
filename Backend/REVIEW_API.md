# Administration and application review

React `/admin/submissions` provides searchable, server-paginated applications. `/admin/submissions/:id` displays the immutable submitted schema, all answers, private file downloads, decisions, append-only notes and review history. The overview uses server aggregates instead of counting a loaded page.

All APIs below require an active Django staff session with Super Admin, Event Admin or Reviewer role and the appropriate model permission. Event Admins and Reviewers see only assigned events. Plain staff, anonymous users and revoked assignments cannot bypass these scopes. Writes retain Django session CSRF checks. Public APIs do not contain reviewer notes, history, contact data, export paths or private provider identifiers.

| Method / path | Behavior |
| --- | --- |
| GET `/api/admin/dashboard/` | Scoped event count, published form count, total submissions, counts for each application status |
| GET `/api/admin/submissions/` | Paginated references, event/form labels, status and timestamps |
| GET `/api/admin/review/forms/` | Scoped form summaries for reviewers and managers, including counts and availability |
| GET `/api/admin/submissions/{uuid}/` | Contact email, submitted schema/answers, authorized attachment metadata, notes and status history |
| PATCH `/api/admin/submissions/{uuid}/status/` | `{"status":"under_review"}`; stores actor, old/new status and timestamp when the status changes |
| POST `/api/admin/submissions/{uuid}/notes/` | `{"body":"Private review assessment"}`; records authenticated author and timestamp; maximum 10,000 characters |
| GET `/api/admin/submissions/export/` | CSV/XLSX for the same filtered result, across all matching pages |
| GET `/api/submission-files/{id}/` | Authorized private attachment; no public/provider URL redirect |

List/export query parameters: numeric `event`, numeric `registration_form`, `status`, `reference_number`, `search` (maximum 200 characters), and `ordering`. Supported ordering values are `submitted_at`, `reference_number`, `status`, each optionally prefixed with `-`. Search matches reference, contact email and dynamic answer text, supporting custom applicant-name field keys. Pagination uses the existing DRF page configuration. New applications means `submitted` status, not a rolling date window. Dashboard counts always reflect the signed-in user's complete event scope.

## Exports and documents

Use `file_format=csv` (default) or `file_format=xlsx`; do not use DRF's reserved `format` parameter. Export removes page selection and includes all matching records. Exports are bounded to 10,000 records, 1,000,000 cells, 20 MiB of text and spreadsheet-supported cell/column lengths. Excess selections return an error rather than silent truncation; narrow the event/form/status filters.

Each export includes reference, event, form, version, email, status, UTC submission timestamp and dynamic answer columns labeled from the **submitted version**. Files and private reviewer notes are intentionally omitted. Values that could be interpreted as spreadsheet formulas are prefixed with an apostrophe, including leading whitespace/control characters and full-width formula operators. XLSX uses text-only cells and contains no formulas, hyperlinks or macros. A small standard-library ZIP/XML writer avoids adding a spreadsheet framework dependency.

CSV and XLSX use authenticated downloads, attachment filenames and private/no-store headers. Frontend downloads fetch credentials to the configured API base and create temporary blob URLs that are revoked after use. `Content-Disposition` is explicitly exposed for permitted cross-origin requests; no CORS wildcard or new trusted origin is introduced. Files are downloaded as attachments with `nosniff` through the existing server-authorized storage service. Documents can then be opened locally; private provider URLs are never exposed.

Each successfully prepared export records actor/action, record count and non-PII filter IDs/status. Private file access records the actor, submission, file ID and timestamp when a download is authorized and opened. This records a prepared download, not proof that every byte reached the browser. Super Admins can inspect read-only access logs in Django Admin. Status history and note authorship are visible on the application; notes cannot be overwritten or deleted through an API. Django Admin also displays read-only note/status history alongside its existing audited status editor.

## Form lifecycle

Form summaries include `submission_count`, `accepting_submissions` and `unavailable_reason`. The existing form workspace now shows these values and paginates its cards. Archive is a confirmed PATCH setting `status=archived`; schemas, submissions, files and history remain intact. Republishing remains an explicit builder action.

POST `/api/admin/forms/{id}/duplicate/` accepts `title`, globally unique `slug` and optional destination `event` ID. Managers must have access to **both** source and destination; Reviewers cannot duplicate. A copy is a new draft with cloned question definitions, zero submissions and no published versions. For a different event, opening/closing dates are cleared so old deadlines are not reused. Review event dates and publish intentionally. Existing forms are never moved between events.

## Local verification

Migration `registrations/0007_reviewaccesslog_reviewernote` creates notes and download/export audit records. Apply normally:

```bash
cd Backend
source .venv/bin/activate
DEBUG=True python manage.py migrate
DEBUG=True python manage.py check
DEBUG=True python manage.py test
```

```bash
cd Frontend
npm run lint
npm run test
npm run build
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome npm run test:e2e
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome python3 scripts/run-admin-integration.py
```

The integration runner uses only disposable accounts, an isolated SQLite database and temporary private files. It covers real session/CSRF operations, uploads, review decisions/notes, exports, private files and denied access to another event. Production Cloudinary, deployed Netlify proxy cookie forwarding and PostgreSQL concurrency require their actual infrastructure and are not implied by local tests. Nothing is deployed.
