# Public event registration

Existing pages, archive definitions, images and layout remain intact. Published Django events have independent registration routes:

- `/events/:slug/register`: published categories for the backend event.
- `/events/:slug/register/:formSlug`: dynamically rendered published schema.
- `/events/:slug/register/:formSlug/confirmation`: successful receipt in the current browser tab.

See [ADMIN.md](ADMIN.md) for API configuration and local startup. Public reads omit credentials and never request an administrator session. Uploads use multipart XMLHttpRequest with progress; no Cloudinary credentials or private file URLs reach public responses.

The renderer supports all thirteen backend field types, required/help text, stable option values, browser validation and inline Django errors. The backend enforces versions, deadlines, capacity, options and file safety. Closed/unavailable/mismatched-event forms cannot be submitted. Confirmation means receipt, not selection or verified payment.

## Editable example templates

Choose an existing backend event ID explicitly:

```bash
cd Backend
source .venv/bin/activate
DEBUG=True python manage.py seed_registration_templates --event 1
# Or select just one:
DEBUG=True python manage.py seed_registration_templates --event 1 --template executive-board
```

These commands create database **drafts** for Delegate Registration and Executive Board Application. Repeated runs skip existing forms and preserve administrator edits. They never import the historical archive, create accounts, publish forms or overwrite questions. Review/edit committee choices, payment instructions, consent, dates and capacity in `/admin/forms` before publication. Every question remains editable through the builder.

## Network errors and privacy

A processing request disables repeated submissions. An uncertain network/server result locks the original answers/files and offers an explicit retry using the same UUID. Django returns the original receipt if it already committed that exact request. No write is retried automatically. A changed request with the same UUID is rejected. Answers/files are held only in memory; sessionStorage contains only an opaque attempt key/version or the successful receipt, never applicant answers, email or phone. No session credentials enter localStorage.

Reload after an uncertain attempt requires re-entering the same answers/files with the retained key. Contact organisers if the form changed. Successful receipts survive reload in the same tab; no public API allows looking up applicants by reference. A new separate application is offered only when the published form explicitly allows multiple submissions.

Local private file storage is temporary; production must configure persistent private storage as described in [SUBMISSIONS.md](../Backend/SUBMISSIONS.md). Upload constraints and duplicate/capacity checks always remain server enforced.

## Checks

`npm run test` covers dynamic controls, validation, server errors, progress, repeat clicks, safe retries, closed forms and storage privacy. `npm run lint` and `npm run build` check all frontend code. `python3 scripts/run-admin-integration.py` runs both administration and public registration browser workflows against an isolated temporary Django database, including real uploads and retry after a lost committed response. No live infrastructure or credentials are used.

## Event discovery integration

`/events` now combines published backend events with the preserved historical archive. Existing historical details remain on their original renderer and URLs. Current backend events have their own details at the existing event route and show registration entry points when an available published form exists. Overlapping slugs or exact normalized title/date identities are deduplicated with archive content taking priority. API downtime leaves the archive usable. Full workflow evidence, matching rules, test commands and external limitations are documented in [INTEGRATION_VERIFICATION.md](../Backend/INTEGRATION_VERIFICATION.md).

## Upcoming events on the homepage

The homepage displays the nearest three upcoming/ongoing published backend events immediately after its hero as a compact list of linked event names and registration buttons, without image cards. The Events page displays all upcoming events first, followed by a separate Past events section. Existing search/year/category filters apply to both sections. Registration links appear while the backend advertises an available published form and the event registration window is still open; closing registration alone does not turn a future event into a past event.

Events leave Upcoming at their exact `end_date`, or `start_date` when no end date is set, and remain available in Past events at the same URL. These are timezone-aware timestamps; displayed dates use Asia/Dhaka. A page-local timer updates at relevant date boundaries and on focus/visibility changes, so an open page also updates without a reload. Historical archive entries remain in Past events and their content/images are unchanged. No scheduled database mutation or deployment is needed.

To show a new upcoming event, set a future start/end date and publish the event in Admin. Publish an open registration form for that event to display its Register button. Unpublished events and forms are never displayed as open registration. The homepage has loading/empty/retry states when there are no announcements or the API is unavailable.
