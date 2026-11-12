# Administrator authentication and permissions

Django's existing User, Group, Permission, database-backed sessions and CSRF middleware provide authentication. No JWT, separate identity framework, browser token storage or new public pages were added. The React administration workspace is now available under `/admin/`; see [Frontend/ADMIN.md](../Frontend/ADMIN.md). `EventAssignment` scopes non-super administrators to specific events. Public event/archive pages and anonymous form submissions remain unchanged.

## First administrator and role provisioning

From the repository root, with your private local `.env` configured:

```bash
cd Backend
source .venv/bin/activate
DEBUG=True python manage.py migrate
DEBUG=True python manage.py setup_admin_roles
DEBUG=True python manage.py createsuperuser
DEBUG=True python manage.py runserver
```

`createsuperuser` prompts interactively for username, contact email and password. Choose a unique strong password, keep Django's password validation enabled, and do not put passwords in command arguments, shell history, source files or committed environment files. No user, password or production secret has been created automatically. `DEBUG=True` above is for local development only. For a future production installation, run the equivalent management commands in an authorized private platform console with the production environment and `DEBUG=False`; do not use local SQLite or development credentials there.

Visit `http://localhost:8000/admin/` and sign in. A Django `is_superuser=True` account is a Super Admin without needing a group. Groups are synchronized after migrations and may also be synchronized explicitly with `setup_admin_roles`. Synchronization resets managed group permissions to their defined policy and never adds users or grants roles to existing staff. Do not customize managed group permissions as a persistent policy change; use custom groups for unrelated features.

To provision another administrator through Django Admin:

1. Create a Django user with an individual strong password; enable **Active** and **Staff status**.
2. Add the user to **Event Admin** or **Reviewer**. Do not enable Superuser status for these roles.
3. In Accounts → Event assignments, associate that user with each authorized event.

Use **Super Admin** group membership only for trusted users intended to have full administration access. It grants broad Django model permissions and full API scope. Only a Super Admin can manage users, groups and event assignments, including in the fallback admin. Organizer references do **not** grant event access. Assignment alone, staff status alone, direct model permissions alone or an unknown group alone do not grant administration access. Inactive/nonstaff users are rejected even if they have a role group.

Roles are group-based and global: a user belonging to both Event Admin and Reviewer has their union of capabilities for all assigned events. Assignments do not themselves carry different per-event roles. Removing an assignment removes that event from subsequent scoped requests; removing the role or disabling the user removes administrator access on subsequent requests.

## Role policy

| Capability | Super Admin | Event Admin | Reviewer |
| --- | --- | --- | --- |
| Create events; choose/change organizer | Yes | No | No |
| View administrative event data | All | Assigned | Assigned |
| Edit/delete events | All, subject to retention | Assigned, subject to retention | No |
| Create/edit/preview/publish/duplicate/close forms | All | Assigned | No |
| View/review applications and private files | All | Assigned | Assigned |
| Change application status | All | Assigned | Assigned |
| Manage users/groups/event assignments | Yes | No | No |

Native Django model permissions are also checked for non-super role capabilities. Reviewers have view/change submission permissions, where change is limited to the existing audited status operation. They cannot rewrite answers, applicant email, files or event/form definitions. Published versions and historical submissions retain their existing immutability/retention rules, including for Super Admins.

Administrative list queries are scoped **before** search/filter/pagination. Another event's IDs or applicant UUIDs do not bypass this scope. Unassigned administrative objects return 404; a forbidden role/action or an unassigned event in a form-create payload returns 403. Private-file access checks happen before storage/provider access. Existing authenticated applicants may still access their own legacy submission files; this does not grant administrator access.

Django Admin uses the same event scope for lists, object pages, related choices and autocomplete endpoints. Only Super Admins can manage accounts/groups/assignments, even if a non-super administrator was accidentally given extra direct auth-model permissions. Submission review status can be changed through either the API or fallback admin and is audited in both cases. Other submitted data and published versions remain read-only.

## Session API

| Method | Path | Result |
| --- | --- | --- |
| GET | `/api/admin/auth/csrf/` | Bootstrap HttpOnly CSRF cookie and return a masked csrf_token |
| POST | `/api/admin/auth/login/` | Authenticate administrator and establish a Django session |
| GET | `/api/admin/auth/me/` | Current administrator/session status |
| POST | `/api/admin/auth/logout/` | Flush server-side session; 204 |

Login input:

```json
{"username":"your-admin-username","password":"entered-at-runtime"}
```

Successful login returns 200:

```json
{
  "authenticated": true,
  "administrator": {
    "id": 2,
    "username": "event-manager",
    "roles": ["Event Admin"],
    "all_events": false,
    "assigned_event_ids": [1]
  },
  "csrf_token": "masked-token-from-server"
}
```

No session cookie value, password or applicant data is returned in JSON. Invalid credentials, inactive accounts and nonadministrators share the same generic 401 error. Missing/bad CSRF or an untrusted Origin returns JSON 403. Login requires CSRF **even for anonymous users**; session authentication's usual authenticated-only CSRF behavior is not relied on for login. Login rotates the session/CSRF state. Use the **new csrf_token returned by login** for subsequent mutations; a token from before login is stale.

An anonymous/expired/nonadministrator `GET /api/admin/auth/me/` returns 200 with `{"authenticated":false,"administrator":null}`. Unauthenticated protected administrative APIs return JSON 403, never an HTML login redirect. Forbidden roles get 403; unassigned object lookups get 404. Logout is POST-only and requires CSRF, including for a harmless already-expired session. All administrative responses, including CSRF bootstrap, carry private/no-store cache headers and vary on Cookie/Origin.

`GET /api/admin/events/` now lists scoped events, and `GET /api/admin/events/{id}/` reads an assigned event for administration. The previous POST/PATCH/DELETE routes remain, with the role restrictions above. Staff application detail also includes the original immutable `form_schema` so reviewers can interpret stable answer keys after later schema edits.

## Recommended Netlify proxy / first-party cookies

Keep React on Netlify and Django on Heroku. Have the browser call relative `/api/...` URLs on the **same public frontend origin**; Netlify proxies those requests over HTTPS to Heroku. Django's host-only cookies then belong to the browser-visible frontend host, so they are first-party. Session cookies use Secure in production, HttpOnly, SameSite=Lax, no Domain override, and `/` path. CSRF cookies are HttpOnly too; the masked token is obtained through the JSON bootstrap endpoint rather than reading document.cookie.

A reviewable [proxy example](deployment/netlify-api-proxy.example.txt) is provided. **Active frontend routing files were not changed**, because there is no actual deployment backend hostname configured. When preparing deployment, replace the example hostname and insert its API rewrite before the existing catch-all in `Frontend/public/_redirects`. This repository has catch-alls in **both** `_redirects` and `netlify.toml`: Netlify processes `_redirects` before TOML rules, so merely adding a TOML proxy before its own catch-all would still be shadowed by the `_redirects` fallback. Preserve public SPA routing after the API rule. This follows Netlify's [rule processing order](https://docs.netlify.com/manage/routing/redirects/overview/) and [proxy documentation](https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/).

Production configuration for this recommended mode:

```text
AUTH_COOKIE_MODE=proxy
DEBUG=False
ALLOWED_HOSTS=<actual-backend-hostname>,<frontend-hostname-if-forwarded-by-your-proxy>
CSRF_TRUSTED_ORIGINS=https://<actual-frontend-origin>
REDIS_URL=<shared-production-Redis-URL>
```

Use actual hostnames without schemes in ALLOWED_HOSTS and exact HTTPS origins in CSRF_TRUSTED_ORIGINS. CORS is unnecessary for browser same-origin proxy calls; production proxy mode defaults to `CORS_ALLOW_CREDENTIALS=False`. Backend proxy/security configuration must correctly identify the original HTTPS request through the trusted router. Do not set Cookie Domain to the Heroku hostname, `.netlify.app`, or a wildcard domain. Never cache auth/administrative proxy responses or overwrite upstream Set-Cookie headers. Verify browser Set-Cookie/session persistence, CSRF, forwarded Host/Origin/HTTPS, cache headers and logout on the real deployment before enabling access.

The direct Heroku `/admin/` fallback uses its own first-party cookies on that hostname. Sign in there independently if needed; a host-only Netlify cookie is not shared with the Heroku hostname. The fallback remains available even when no React administration UI exists.

Browser example for future integration (documentation only):

```js
const api = '/api';
let csrfToken; // Memory only. Never persist session secrets in localStorage.

const bootstrap = await fetch(`${api}/admin/auth/csrf/`, {
  credentials: 'include', cache: 'no-store'
}).then(r => r.json());
csrfToken = bootstrap.csrf_token;

const loginResponse = await fetch(`${api}/admin/auth/login/`, {
  method: 'POST', credentials: 'include',
  headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
  body: JSON.stringify({username, password}) // From the login form at runtime.
});
if (!loginResponse.ok) throw new Error('Administrator login failed');
const session = await loginResponse.json();
csrfToken = session.csrf_token; // Login rotates CSRF state.

const current = await fetch(`${api}/admin/auth/me/`, {
  credentials: 'include', cache: 'no-store'
}).then(r => r.json());

const logoutResponse = await fetch(`${api}/admin/auth/logout/`, {
  method: 'POST', credentials: 'include', headers: {'X-CSRFToken': csrfToken}
});
if (!logoutResponse.ok) throw new Error('Logout failed');
csrfToken = undefined;
```

Use X-CSRFToken and credentials for every administrative POST/PATCH/DELETE. Handle 403 by checking session status, then either reauthenticate or show access denied; handle a scoped 404 as unavailable without disclosing another event's data. Do not automatically retry non-idempotent mutations after a login/CSRF failure. Do not log password input or store session IDs, passwords or authentication secrets in browser storage. Cookie contents are managed by the browser, not JavaScript. Django's [CSRF documentation](https://docs.djangoproject.com/en/5.2/howto/csrf/) explains token/Origin validation and AJAX headers.

## Local split-origin development

Run the backend as `http://localhost:8000` and Vite as `http://localhost:5173`. Use the same hostname for both (do not mix localhost with 127.0.0.1 for cookie testing). Development defaults allow credentialed CORS for the explicit `http://localhost:5173` origin and trust it for CSRF. Use the bootstrap JSON token, `credentials:'include'`, and X-CSRFToken as above, with API base `http://localhost:8000/api`. Development cookies use SameSite=Lax and are not Secure over local HTTP. There are no broad CORS allowances and no CSRF bypass. The admin API adapter supports this flow through VITE_API_BASE_URL; no Vite proxy configuration is required for split-origin development.

## If direct cross-site cookies are unavoidable

Opt in only for production HTTPS:

```text
AUTH_COOKIE_MODE=cross_site
DEBUG=False
CORS_ALLOWED_ORIGINS=https://<exact-Netlify-or-custom-frontend-origin>
CSRF_TRUSTED_ORIGINS=https://<same-exact-origin>
CORS_ALLOW_CREDENTIALS=True
```

This sets both session/CSRF cookies to literal SameSite=None while retaining Secure and HttpOnly. Startup rejects debug HTTP, missing credentialed CORS, wildcard/non-HTTPS origins or CORS origins not explicitly trusted for CSRF. Keep host-only cookies on the backend; bootstrap by fetching the backend CSRF endpoint with credentials included, then send the JSON token in X-CSRFToken to that same API. CSRF protection is retained, not disabled to fix CORS errors.

Browsers may still block third-party cookies even with correct attributes; no backend flag can guarantee availability. Prefer the first-party proxy design. Live cross-site browser behavior must be verified on the intended domains; no proxy or deployment was activated here.

## Limits, session lifetime and verification

Login attempts are limited at both API and `/admin/login/`: defaults 10/minute and 100/hour per inferred client IP, plus 10/15 minutes per normalized username. Configure `LOGIN_RATE_PER_MINUTE`, `LOGIN_RATE_PER_HOUR`, `LOGIN_USERNAME_RATE_PER_15_MINUTES`. Limits use fixed-window atomic cache counters with server-keyed HMAC identifiers; usernames and IPs are not stored as plaintext keys. Valid-CSRF failed and successful login attempts consume quota. 429 includes Retry-After. Production requires the existing shared Redis configuration; unavailable/missing caching fails closed with a generic 503.

`TRUSTED_PROXY_COUNT` affects inferred client IP. Keep the existing safe default of one trusted Heroku hop unless the actual proxy chain is verified. Through an extra Netlify proxy, that can aggregate clients under proxy egress IPs; validate quotas against real traffic before rollout. Do not blindly increase the count on a publicly reachable backend, where attacker-supplied forwarding entries could spoof identity. Per-username limits remain independent of proxy IP grouping. Production perimeter/proxy configuration is a deployment integration task, not an assumption of this implementation.

`ADMIN_SESSION_MAX_AGE` defaults to 28,800 seconds (8 hours). Session storage is database-backed, cookies expire at browser close subject to browser session-restoration behavior, and DB expiry still applies. Logout flushes server-side state. Run Django's `clearsessions` periodically through your operational scheduler when hosting is provisioned. Group/assignment changes take effect on fresh requests without needing to copy permissions into a browser token.

```bash
DEBUG=True python manage.py check
DEBUG=True python manage.py makemigrations --check --dry-run
DEBUG=True python manage.py test
```

Before future production exposure, run `check --deploy` with real environment configuration and perform browser/proxy tests. Automated tests cover all roles, unassigned records, private files, role revocation, fallback admin scoping, foreign-key choices, status audits, CSRF/Origin rejection, session rotation/logout, generic credential failures, login quotas/cache failure, and production cookie configuration. Real Netlify/Heroku cookie forwarding, browser third-party policy and shared production Redis/PostgreSQL behavior remain external integration checks.
