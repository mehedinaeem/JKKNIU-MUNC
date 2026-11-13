# Public submissions and private files

This extends the dynamic schema engine; the public React integration is documented in [REGISTRATION.md](../Frontend/REGISTRATION.md). Nothing has been deployed. Definitions still live in the database; published versions remain immutable. `FormSubmission` replaces the earlier internal `Submission` model through a data-preserving rename/backfill migration. Existing answers, IDs, version links, timestamps and legacy file paths are retained. Historical records without a known email retain a blank value; all new submissions require an email. The old Python import name remains an alias for compatibility.

## Public API

First read `GET /api/forms/{slug}/` to obtain the current published version. Then:

```http
POST /api/forms/conference-2027-delegates/submit/
Content-Type: application/json
```

```json
{
  "version": 1,
  "applicant_email": "applicant@example.com",
  "answers": {
    "full_name": "Example Applicant",
    "committee": "unga",
    "consent": true
  }
}
```

The example answer keys must match the actual published schema. A 201 response contains only:

```json
{
  "reference_number": "JM-1B11917CC48248ADAD8D8969B744394B",
  "message": "Your application has been received."
}
```

The reference is unique and random, with no email, sequence number or other applicant information encoded in it. It is a receipt identifier, **not an access token**. There is no public lookup endpoint for submissions, references, statuses, answers or files. Public responses never contain provider URLs, file IDs, private download links, applicant email, phone or previous answers. Responses use `Cache-Control: no-store`.

This route intentionally accepts anonymous submissions without session cookies. Browser access is still limited to configured CORS origins; CORS itself is not an anti-abuse control. The existing `/api/forms/{slug}/submissions/` route remains authenticated and CSRF protected for compatibility. It uses the account email as its applicant email, invokes the same admission/storage service and rate limits, and retains its earlier owner-specific response/download behavior. Administrator session endpoints are now available as described in [AUTHENTICATION.md](AUTHENTICATION.md); no public account-registration API was added.

Every answer is checked server-side against the **current immutable published version**. Stale version numbers, unknown answer/file keys, missing required answers, invalid options or mismatched types return 400. Draft/unpublished/closed/archived forms or unpublished events return 404. Published but not-yet-open, expired or full forms reject admission with 400. Form/event opening bounds are inclusive, closing bounds exclusive, and event start is the final registration cutoff.

Email is stripped and case-folded for duplicate checking across all versions of the same form. If multiple submissions are disabled, a prior matching email is rejected with a generic error that does not reveal any stored data; the authenticated compatibility route also checks its account identity. This checks the supplied contact address, not email ownership. No email verification or alias-domain rewriting is performed, so this is not proof of a person's identity. Email fields within dynamic answers remain independently validated schema answers; `applicant_email` is the canonical contact/duplicate identity.

PostgreSQL row locks serialize admission against publish/edit/status/window changes, and conditional counter updates enforce capacity. Counter increments, submission/file records and cleanup-intent removal commit together. A failed admission or database commit rolls back capacity. A stale administrative model save cannot reset the counter. Review statuses do not free slots. SQLite remains development-only for multi-writer workloads.

## Staff review

Use an authenticated active Super Admin, Event Admin or Reviewer session, scoped to assigned events, with CSRF tokens for mutations. Staff status alone no longer grants access; see [AUTHENTICATION.md](AUTHENTICATION.md):

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET | `/api/admin/submissions/` | Paginated summaries, no email/answers |
| GET | `/api/admin/submissions/{uuid}/` | Applicant email, validated answers, file metadata and protected application download paths |
| PATCH | `/api/admin/submissions/{uuid}/status/` | Change status only; create actor/timestamp audit entry |
| GET | `/api/submission-files/{id}/` | Staff streams a private attachment; authenticated legacy owners may access their own files |

List filters: `event` and `registration_form` numeric IDs, exact `reference_number`, and `status`. Invalid filter values return 400. Results use the existing 25-item pagination. All staff/file responses are `private, no-store`. Anonymous, nonadministrator, nonstaff and unassigned users cannot read submission detail or change status. Lists are scoped before filters and pagination. Anonymous applicants cannot retrieve files with their reference number.

```http
PATCH /api/admin/submissions/1f295c4d-6fb9-4fab-8f14-79755fedb8ee/status/
Content-Type: application/json
X-CSRFToken: <authenticated staff CSRF token>
```

```json
{"status":"under_review"}
```

Allowed statuses: `submitted`, `under_review`, `shortlisted`, `approved`, `rejected`, `waitlisted`. Additional properties such as answers, applicant_email or files are rejected by this endpoint. The 200 response is the updated summary with reference, linked IDs, status and timestamps. Staff detail is required for PII and answers. Changes are audited with previous/new status, actor and time. Django Admin permits scoped, audited status review as a fallback; all other submitted data remains read-only.

An uploaded payment receipt or transaction screenshot is **unverified evidence only**. Uploading it does not verify a payment, mark a submission paid, or approve an application. This backend does not integrate a payment provider or perform payment verification.

## File submissions

Only PDF, PNG and JPEG (`pdf`, `png`, `jpg`, `jpeg`) are accepted. Configure each published file field with `allowed_extensions` and `max_file_size` in bytes. Global maximum is 10 MiB per file and 20 MiB of uploaded bytes per request, with up to 10 files. JSON submission bodies are limited to 2 MiB. Django's first upload handler enforces cumulative bytes before permanent storage; native Django/CSRF and DRF parsing share the limit.

```bash
curl -X POST http://127.0.0.1:8000/api/forms/example/submit/ \
  -F 'payload={"version":1,"applicant_email":"applicant@example.com","answers":{"name":"Example"}}' \
  -F 'document=@./application.pdf;type=application/pdf'
```

Use file parts named after the schema's stable field keys, and a text `payload` part containing version/email/answers JSON. Files cannot also appear as JSON paths/URLs or be supplied twice under one key. Undeclared file keys are rejected. All fields/files are validated before provider uploads begin.

Validation checks extension, actual size, declared MIME type and parsed content. Browser MIME headers alone are not trusted. PNG/JPEG images are decoded, dimensions limited to 16 million pixels, verified and re-encoded to strip metadata/appended payloads. Resulting bytes must still fit the configured limit. PDFs require a valid signature/trailer and parseable unencrypted content, 1–200 pages and bounded object complexity; embedded files, JavaScript/actions and interactive form features are rejected. MIME mismatch, executables, SVG/HTML, damaged files and unsupported documents are rejected. Parser details are not returned to applicants. These checks are not an antivirus guarantee.

Original filenames are normalized to a safe basename and available only to staff. Stored provider names use random IDs without applicant data. Downloads use a generated attachment filename, `application/octet-stream`, `nosniff` and private/no-store headers. No public media route is added.

## Storage configuration

Development defaults to `SUBMISSION_STORAGE_PROVIDER=temporary`, writing private mode-0600 files beneath a mode-0700 directory in the OS temporary directory. `LOCAL_PRIVATE_UPLOAD_ROOT` can select another development-only temporary directory. Files are not served directly. Temporary files may disappear after reboot/OS cleanup; they are not production storage.

Production (`DEBUG=False`) permits only `SUBMISSION_STORAGE_PROVIDER=cloudinary`. Set these server-side environment variables using your actual provider account:

```text
SUBMISSION_STORAGE_PROVIDER=cloudinary
CLOUDINARY_CLOUD_NAME=<cloud name>
CLOUDINARY_API_KEY=<API key>
CLOUDINARY_API_SECRET=<API secret>
RATE_LIMIT_BACKEND=auto
# Optional: REDIS_URL=<shared Redis connection URL>
```

Alternatively use `CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>`; it takes precedence over individual Cloudinary variables. No real credentials or production secrets are provided. Never add these values to frontend/Vite variables, browser uploads, source control, screenshots or application logs.

The adapter uploads through the server SDK with `resource_type=raw`, `type=authenticated`, randomized public_id, and overwrite disabled. Original images/documents and derived resources therefore require authentication. Downloads are authorized by Django, then proxied server-side using a short-lived signed Cloudinary API download URL; the browser never receives that provider URL. No public Cloudinary delivery fallback is used. These choices follow Cloudinary's [authenticated asset guidance](https://cloudinary.com/documentation/upload_parameters) and [time-limited download documentation](https://cloudinary.com/documentation/control_access_to_media).

Filesystem storage is rejected for production submissions, including on Heroku. Missing credentials or provider failures fail closed with a generic 503. No Cloudinary account, Redis instance or paid service has been provisioned. Part 3's `PRIVATE_UPLOAD_STORAGE_BACKEND` alias is retained **only for reading historical files**, not for new submission writes; migrate any real legacy local files to persistent storage as a separately reviewed operation before hosting them on Heroku.

## Rate limits

Defaults are 5 attempts/minute and 30/hour per client IP, plus 5/hour per normalized applicant email. Configure `SUBMISSION_RATE_PER_MINUTE`, `SUBMISSION_RATE_PER_HOUR`, and `SUBMISSION_EMAIL_RATE_PER_HOUR` as positive integers. Invalid attempts also consume quota. Exceeding quota returns 429 with Retry-After. Fixed-window counters use cache add/increment rather than a read/modify/write list; cache identities use a server-keyed HMAC instead of plaintext IP/email.

Login, membership and public submissions use the shared database limiter when REDIS_URL is absent, including in development. Production uses PostgreSQL; Redis remains optional when configured. A failure of the selected store returns a generic 503 rather than disabling throttling or switching budgets. See RATE_LIMITING.md for migration and expired-counter cleanup. Use your provider's TLS Redis URL where required. `TRUSTED_PROXY_COUNT` defaults to zero locally and one behind the intended Heroku router. Configure it for the actual trusted proxy chain so client-supplied forwarding headers cannot bypass quotas. Apply platform request-body limits consistent with the application upload policy. No rate-limit/bot protection can establish anonymous applicant identity by itself.

## Orphan cleanup and operations

A durable `UploadCleanup` intent with a random provider ID is written **before** any remote upload and before the admission transaction. The admission transaction locks its intents so a cleanup worker cannot delete an in-flight asset. Successful submission linking and intent removal commit together. Upload timeouts, metadata-save failures or commit failures trigger compensating provider deletion after rollback. No partial submission or consumed slot remains. A failed deletion retains its intent and increments the retry count; log messages contain only intent IDs, not emails, filenames, provider errors or credentials.

Run this command periodically from your existing operational scheduler/process when deploying:

```bash
python manage.py cleanup_uploads
```

It retries at most 100 intents older than one hour and never deletes a provider ID referenced by a committed file record. `--min-age-seconds` must be at least 300 and should exceed the longest permitted request/upload duration; `--limit` accepts 1–500. PostgreSQL workers skip locked in-flight intents. A worker/process crash leaves a durable task for later retry. No scheduler or deployment has been configured. Monitor persistent intents and back up submission data using the hosting/database provider's controls.

Run local validation after configuring `.env`:

```bash
python -m pip install -r requirements.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test
```

Before a future production release, run `python manage.py check --deploy` with actual Cloudinary, Redis and PostgreSQL configuration. Deployment checks flag missing private storage/shared rate limiting. Live provider delivery, real Redis multi-worker behavior, PostgreSQL concurrency and Heroku integration require separately provisioned infrastructure and were not executed locally. Cloudinary calls are mocked in tests; local uploads, real SQLite transactions, forced commit failures and data-preserving migrations are exercised.

## Safe browser retries

Optional `submission_key` is a UUID per application attempt. Identical retries return the original receipt, including after the form closes, without consuming another capacity slot or uploading files again. The server fingerprints the normalized contact email, version, answers and file metadata/bytes. Reusing a key with different data returns a generic validation error. There is no public reference lookup. Browser retry keys are not session credentials. Migration `0006` adds the nullable key/digest and per-form unique constraint; existing submissions remain intact.
