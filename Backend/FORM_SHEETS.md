# Per-form registration sheets

Open the React admin **Form sheets** menu (`/admin/sheets`) and choose a registration form. Each form has its own route, `/admin/sheets/{form_id}`, so responses from different forms remain separate. Registration form cards also include **View response sheet**, and filtered Applications lists offer **Open form sheet**.

Each applicant is one row. Columns include reference, contact email, review status, submission date, submitted version, and every question published under that form. Removed questions remain visible for historical responses; newly added questions show a dash for versions that never asked them. Headers use the most recent published label for each stable field key. Each cell uses its own immutable submitted schema for option labels and field types; if its original question label differs, it displays “Asked as”. The reference opens the existing application review page for status decisions, private notes and audit history.

The sheet supports search by name/email/reference, status filters, ordering, server pagination, manual refresh and existing CSV/XLSX text exports for the chosen form and filters. The question columns remain stable across pages and filters. Scroll the table horizontally to see all questions; the header and reference column stay visible. Sheets are read-only, so viewing answers cannot accidentally overwrite a response.

## Private images and files

PNG and JPEG uploads appear as lazy-loaded thumbnails. **Enlarge image** opens a protected larger preview; **Download file** uses the existing authorized original download. PDFs remain protected attachments. Previews are not public/provider URLs, and images are not embedded in text exports.

- GET `/api/admin/forms/{id}/sheet/` returns paginated submitted answers/files, stable question columns and form metadata. The same Super Admin/Event Admin/Reviewer rules and event-assignment scope apply as application review. Public and plain staff access is denied. Each row includes the immutable submitted schema; notes and full review history remain on the individual review screen.
- GET `/api/submission-files/{id}/preview/` returns a maximum 160 × 160 image thumbnail.
- GET `/api/submission-files/{id}/preview/?size=large` returns a maximum 1200 × 1200 image.

Every preview rechecks staff review permission for the file's event, including after role/assignment changes. The server reads at most 10 MiB, checks PNG/JPEG format and image dimensions, decodes/re-encodes and strips metadata. It never serves SVG, HTML or a provider redirect as an image. Unsupported historical local attachments can still use the original authorized download; previews are limited to supported private storage assets. Failed/corrupt previews return a generic error without storage identifiers.

Preview responses are private/no-store with `nosniff`; successful preview access is recorded in the existing review access audit. Cloudinary stays server-side, while temporary development files use the existing private provider. No new permanent Heroku media storage is introduced. The browser uses credentialed, no-store fetches to create temporary blob URLs, aborts pending requests on unmount, and revokes URLs when the preview or page closes. No applicant data or image URL is stored in localStorage/sessionStorage.

No new model migration or dependency is required. Tests cover separate forms, current/removed/renamed questions across versions, pagination, role/assignment revocation, private bounded previews and corrupt/unsafe file rejection. React tests verify historical display values, sheet switching, denied access, image-only response validation and blob cleanup. Real Django browser integration verifies an assigned reviewer can open a form sheet, view/enlarge a real image, change sheets and use the responsive scrollable layout.
