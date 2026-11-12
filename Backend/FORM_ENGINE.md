# Dynamic form engine

Definitions live in `RegistrationForm` and `FormField`, edited through staff APIs or Django Admin. No Django/React source changes are needed to add questions. The existing frontend is unchanged and does not render these schemas yet.

## Drafts and immutable versions

Each form has an editable working draft. Fields have stable keys, unique within that form, with database uniqueness enforcement. Existing keys cannot be renamed on a saved FormField; remove the draft question and add a new key to create a different question. The same key must keep the same meaning across revisions. Options also have stable values independent of their display labels.

Publishing atomically creates an immutable `FormVersion` with a sequential number and complete JSON schema (title, description, type, ordered questions, constraints and options). Model save/delete, queryset update/delete, and admin editing of versions are blocked. Draft edits, including removing questions, do not change a published snapshot. Submissions reference a protected version and retain their original answers. Published forms cannot be deleted through cascading event/form deletion because versions are protected; close/archive them instead.

Public reads use only the latest published snapshot. Publishing another version changes the current public schema; requests carrying a stale version are rejected and must reload. Editing working-draft questions does not take a currently published form offline. Set status to `draft`, `closed` or `archived` to withdraw it. Set status to `published` only through the publish operation. Reopening uses publish and creates another version.

The existing globally unique form slug avoids collisions between events. A slug edit changes the API URL immediately; there is no old-slug redirect. An existing form cannot move to another event.

## Endpoints

| Method | Path | Access / result |
| --- | --- | --- |
| GET | `/api/events/{event_slug}/forms/` | Public paginated list of published forms for a published event |
| GET | `/api/forms/{form_slug}/` | Published snapshot and availability |
| POST | `/api/admin/forms/` | Staff creates draft, optionally with fields |
| GET / PATCH | `/api/admin/forms/{id}/` | Staff reads/edits draft and operational settings |
| GET | `/api/admin/forms/{id}/preview/` | Staff previews draft schema |
| POST | `/api/admin/forms/{id}/publish/` | Staff publishes new immutable version; 201 |
| POST | `/api/admin/forms/{id}/duplicate/` | Staff copies working draft; 201 |
| POST | `/api/forms/{form_slug}/submissions/` | Authenticated applicant submits answers; 201 |
| GET | `/api/submission-files/{id}/` | Applicant owner or staff downloads private attachment |

Staff writes require an active authenticated staff session and a valid CSRF token. Anonymous submissions are now supported at `/api/forms/{slug}/submit/` with a required applicant email; see [SUBMISSIONS.md](SUBMISSIONS.md). The older `/submissions/` route retains authenticated access. There is no new account/login API. Same-origin Django session authentication is retained; cross-origin Netlify login is not added. Django Admin supports field editing/order, JSON preview, publish/close/archive/duplicate actions, and read-only submission review.

Public unpublished forms/events return 404. Closed/archived forms are also hidden. A published form outside its window or at capacity is readable with `accepting_submissions: false`; its submission endpoint returns 400. Field errors return 400, unauthorized sessions 403, missing objects 404. Public form lists use the configured 25-item pagination.

## Create, edit, publish

Example staff `POST /api/admin/forms/` (use an existing event ID):

```json
{
  "event": 1,
  "title": "Delegate Application",
  "slug": "conference-2027-delegates",
  "form_type": "delegate-application",
  "capacity": 50,
  "allow_multiple_submissions": false,
  "opens_at": "2027-01-01T00:00:00+06:00",
  "closes_at": "2027-02-20T23:59:00+06:00",
  "fields": [
    {
      "key": "full_name",
      "field_type": "short_text",
      "label": "Full name",
      "help_text": "Use your preferred name.",
      "placeholder": "Your name",
      "required": true,
      "display_order": 0,
      "validation": {"min_length": 2, "max_length": 150}
    },
    {
      "key": "email",
      "field_type": "email",
      "label": "Email address",
      "required": true,
      "display_order": 1
    },
    {
      "key": "committee",
      "field_type": "dropdown",
      "label": "Preferred committee",
      "required": true,
      "display_order": 2,
      "options": [
        {"value": "unga", "label": "General Assembly"},
        {"value": "unsc", "label": "Security Council"}
      ]
    },
    {
      "key": "consent",
      "field_type": "consent",
      "label": "I agree to the registration terms",
      "required": true,
      "display_order": 3
    }
  ]
}
```

The 201 response contains the saved form metadata, ID, timestamps and normalized field definitions; status defaults to draft. Custom form types are free text. For `PATCH /api/admin/forms/{id}/`, omit `fields` to preserve all questions. If supplied, **fields replaces the complete working-draft field list**: include every desired question with key/type/label, even in a PATCH. Existing keys preserve their field identity; omitted keys are deleted from the draft; new keys are added. Optional properties omitted from a complete question reset to their documented defaults. Set display_order to reorder; ties use existing field IDs. The whole operation is transactional. Duplicate keys, incomplete question definitions or malformed constraints cause 400 without partial updates.

`GET /api/admin/forms/{id}/preview/` returns `{"draft":true,"schema":{...}}`, including current working-draft questions, without publishing. No React preview UI is added in this phase.

`POST /api/admin/forms/{id}/publish/` needs no body. It validates at least one and at most 100 questions and returns:

```json
{"id":1,"version":1,"schema":{"title":"Delegate Application","description":"","form_type":"delegate-application","fields":[]}}
```

The example above abbreviates `fields`; the real response includes all published question definitions. An empty form cannot publish.

`PATCH /api/admin/forms/{id}/` with `{"status":"closed"}` or `{"status":"archived"}` closes/archives it. `POST /api/admin/forms/{id}/duplicate/` with `{"title":"New application","slug":"new-application"}` copies working-draft metadata/questions into a new draft with zero submissions and no published versions. Existing dates/capacity are copied; review them before publishing. Source responses and versions are never copied. Django Admin's duplicate action generates a unique draft slug.

## Supported types and bounded validation

Every field stores key, label, help_text, placeholder, required, display_order, default_value, validation, options, allowed_extensions and max_file_size. Defaults: optional, order zero, empty strings/rules/options/extensions and null default/file size. Key is a slug of up to 100 characters. Labels/placeholders are up to 255 characters. Help text is limited to 10,000 characters at publication/API validation.

| Type | Answer shape | Allowed validation keys |
| --- | --- | --- |
| `short_text` | String, up to 10,000 characters | min_length, max_length |
| `long_text` | String, up to 100,000 characters | min_length, max_length |
| `email` | Valid email string | min_length, max_length |
| `phone` | Optional leading +, digits/spaces/parentheses/hyphens; 7–15 digits | min_length, max_length |
| `integer` | Whole number or numeric string | min_value, max_value |
| `decimal` | Finite number/string; at most six decimal places | min_value, max_value |
| `date` | YYYY-MM-DD | min_date, max_date |
| `dropdown`, `radio` | One stable option value | No extra rules |
| `checkboxes` | Array of distinct stable option values | min_choices, max_choices |
| `file` | Actual multipart file; no path/URL accepted | File-specific properties below |
| `url` | HTTP(S) URL string | min_length, max_length |
| `consent` | Boolean; true required when required | No extra rules |

Email/phone/URL strings also have a 1,000-character safety ceiling. Numbers must be finite and within ±999999999999999999. Decimal answers are stored as canonical strings to preserve precision; integer answers are stored as integers. Boolean values are not accepted as numbers. Bound values must be valid and minimum cannot exceed maximum. Arbitrary expressions and regex rules are rejected; nothing is evaluated or executed.

Selection options are objects with exactly `value` and `label`, each nonempty strings of at most 255 characters. Values must be unique; there may be at most 200 options. Defaults, where supported, must pass the same type/rule/option validation. File/consent defaults are forbidden. Defaults are presentation hints, never substituted for a missing required answer or preaccepted consent. Empty optional answers are omitted; unknown answer keys and duplicate checkbox choices are rejected.

## Existing authenticated submission route

Example `POST /api/forms/conference-2027-delegates/submissions/`:

```json
{
  "version": 1,
  "answers": {
    "full_name": "Example Applicant",
    "email": "applicant@example.com",
    "committee": "unga",
    "consent": true
  }
}
```

Example 201 response:

```json
{"id":"c4fa8213-ad6a-4267-bd4c-32433b6f085f","version":1,"created_at":"2027-01-05T10:00:00+06:00","files":[]}
```

Example required/option errors:

```json
{"answers":{"full_name":"This field is required.","committee":["Invalid choice."]}}
```

Admission requires published event/form plus a published version. Opening bounds are inclusive; closing bounds are exclusive. Both the event registration window and form window are enforced; event start is a final cutoff even if a later form closing date is configured. Null boundaries do not add restrictions. The service checks current status/windows/capacity again inside its transaction, not just when the schema is read.

PostgreSQL row locks serialize submission/publish/draft writes for each form, and event locks protect admission checks. An atomic conditional capacity increment is rolled back if submission persistence fails. Duplicate prevention spans all versions of a form for the same authenticated account, unless multiple submissions are enabled. Administrative metadata saves cannot overwrite the internal submission counter. Capacity is per form, not per event/version; decreasing capacity below existing count stops new submissions. There is no cancellation/retraction endpoint in this phase. SQLite is for local development; multi-writer deployment requires PostgreSQL.

## Public submissions, staff review and private files

See [SUBMISSIONS.md](SUBMISSIONS.md) for the current public `/submit/` API, staff review/status endpoints, image/PDF content validation, private authenticated Cloudinary delivery, rate limits and retryable cleanup. Supported file extensions are now restricted to pdf/png/jpg/jpeg; earlier text/office document extensions are no longer accepted. The legacy storage alias is retained for historical reads only. New local files use private temporary storage, and new production files require Cloudinary.

## Validation

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test
```

Coverage includes every answer type, required/default behavior, invalid options/rules/files, draft visibility, staff/CSRF permissions, duplicate keys, draft edits and immutable version preservation, stale versions, deadlines, capacity, duplicate submissions, duplication and private download ownership. Live PostgreSQL concurrency, external private storage and Heroku infrastructure are not available locally and remain deployment integration checks.
