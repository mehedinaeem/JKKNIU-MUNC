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
