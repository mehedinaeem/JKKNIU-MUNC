# Event management

Run migrations with the local environment configured as described in [README.md](README.md):

```bash
cd Backend
source .venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo_events
python manage.py runserver 127.0.0.1:8000
```

`seed_demo_events` is optional, explicit, restricted to `DEBUG=True`, and idempotent. It creates one clearly fictional published demo conference and four draft example forms. It never imports `Frontend/src/data/events.js` or `eventDescriptions.js`, overwrites existing records, or creates credentials. Type values are arbitrary strings, not an enum of those examples.

## Endpoints

| Method | URL | Access | Success |
| --- | --- | --- | --- |
| GET | `/api/events/` | Public, published only | 200 paginated results |
| GET | `/api/events/{slug}/` | Public, published only | 200; otherwise 404 |
| POST | `/api/admin/events/` | Active authenticated staff | 201 |
| PATCH | `/api/admin/events/{id}/` | Active authenticated staff | 200 |
| DELETE | `/api/admin/events/{id}/` | Active authenticated staff | 204, no body |

Staff can modify any event status using numeric IDs. Public endpoints exclude draft, completed and cancelled events even for staff; a status query cannot override this. This phase does not add a staff list/retrieve endpoint. Staff can browse all events and forms in Django Admin at `/admin/`.

The existing session authentication is used: sign into Django Admin, then send same-origin API requests with the session cookie and `X-CSRFToken` header containing the CSRF token. Browser developer tools or a session-aware HTTP client can be used. Keep CSRF protection enabled. Anonymous/nonstaff/inactive users receive 403, and session writes without a valid CSRF token receive 403. Cross-origin cookie login from Netlify is not implemented. `createsuperuser` prompts locally; no credentials are shipped.

## Event fields and validation

`title`, `slug`, `event_type`, and `start_date` are required on create. Slugs are explicit and globally unique. `status` is one of `draft` (default), `published`, `completed`, `cancelled`. Optional strings default to empty. `end_date`, `registration_start`, `registration_end`, and `organizer` may be null. Organizer is a user ID and defaults to the creating staff member when omitted; explicit null is supported. All returned IDs/timestamps are read-only.

Dates use ISO 8601 with timezone offsets. Django stores aware timestamps in UTC and renders them using Asia/Dhaka (`+06:00`). Prefer explicit offsets in requests. End values cannot precede their respective start values; equality is allowed. Either registration boundary can be absent. No rule tying registration windows to event dates is imposed. PATCH validates incoming values together with the existing record. Invalid fields/duplicates return 400 with field-specific errors. Database constraints additionally protect window order for direct writes.

`cover_image` is an optional full URL reference, for example a publicly hosted asset URL. No upload endpoint or frontend image migration is provided. Changing a slug changes its public API URL; no alias redirect is created.

Example staff create request:

```http
POST /api/admin/events/
Content-Type: application/json
X-CSRFToken: <token from your authenticated session>
```

```json
{
  "title": "Development Conference",
  "slug": "development-conference",
  "short_description": "Fictional example for API development.",
  "description": "A sample event created through the staff API.",
  "event_type": "conference",
  "venue": "Demo auditorium",
  "start_date": "2027-03-01T09:00:00+06:00",
  "end_date": "2027-03-03T18:00:00+06:00",
  "registration_start": "2027-01-01T00:00:00+06:00",
  "registration_end": "2027-02-20T23:59:00+06:00",
  "status": "draft",
  "cover_image": ""
}
```

Example 201 response (IDs/timestamps vary):

```json
{
  "id": 2,
  "title": "Development Conference",
  "slug": "development-conference",
  "short_description": "Fictional example for API development.",
  "description": "A sample event created through the staff API.",
  "event_type": "conference",
  "venue": "Demo auditorium",
  "start_date": "2027-03-01T09:00:00+06:00",
  "end_date": "2027-03-03T18:00:00+06:00",
  "registration_start": "2027-01-01T00:00:00+06:00",
  "registration_end": "2027-02-20T23:59:00+06:00",
  "status": "draft",
  "cover_image": "",
  "organizer": 1,
  "created_at": "2026-11-12T13:00:00+06:00",
  "updated_at": "2026-11-12T13:00:00+06:00"
}
```

Publish with `PATCH /api/admin/events/2/` and `{"status":"published"}`. The response has the same fields, with status and updated timestamp changed. `GET /api/events/development-conference/` then returns that representation. `DELETE /api/admin/events/2/` returns 204 and also deletes associated registration forms.

## Pagination, search, filtering and ordering

Public list parameters:

- `page`: page number; 25 records per page. Invalid/out-of-range pages return 404.
- `event_type`: exact custom type value.
- `search`: case-insensitive substring across title, short description, description and venue.
- `start_date_after`, `start_date_before`: inclusive ISO 8601 datetime bounds.
- `ordering`: `start_date`, `created_at`, `title`, or the same prefixed with `-` for descending. Default `-start_date`; ties use descending ID.

Malformed date bounds or unsupported ordering return 400. Unknown parameters are ignored; there is no public status override.

```bash
curl --get http://127.0.0.1:8000/api/events/ \
  --data-urlencode 'event_type=conference' \
  --data-urlencode 'search=Demo' \
  --data-urlencode 'ordering=start_date' \
  --data-urlencode 'start_date_after=2027-01-01T00:00:00Z'
```

List responses have `count`, `next`, `previous`, and `results`; results use the complete event representation shown above. For an empty search:

```json
{"count":0,"next":null,"previous":null,"results":[]}
```

Example validation error:

```json
{"end_date":["Must be on or after start_date."]}
```

## Registration forms

Manage forms separately in Django Admin or inline under an event. The serializer is available for a future API; this phase does not expose form endpoints or private form data through public event responses.

Fields: event foreign key, title, globally unique slug, description, free-text form_type, status (`draft`, `published`, `closed`, `archived`), optional opens_at/closes_at, nullable capacity (null means unlimited, otherwise >=1), allow_multiple_submissions (default false), and read-only creation/update timestamps. Model validation and database constraints enforce ordered windows and capacity. There is no submission/capacity enforcement workflow yet; these fields store configuration only.

Example `RegistrationFormSerializer` input for internal code (not an HTTP route):

```json
{
  "event": 2,
  "title": "Research Fellowship Application",
  "slug": "development-conference-research-fellowship",
  "description": "An administrator-defined custom application.",
  "form_type": "research-fellowship",
  "status": "draft",
  "opens_at": "2027-01-01T00:00:00+06:00",
  "closes_at": "2027-02-20T23:59:00+06:00",
  "capacity": 30,
  "allow_multiple_submissions": false
}
```
