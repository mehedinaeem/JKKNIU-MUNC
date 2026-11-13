# Member management and secure account activation

## Architecture and available routes

The existing project used Django's built-in User, session cookies, CSRF, role groups, event assignments, a private Cloudinary/temporary file adapter, and a Brevo database queue. It had no membership or authorized university verification integration; Join Us linked to Contact. This implementation keeps the established user model, authentication backend, public events/archive, registration forms and hosting split. `/contact` remains available; the existing Join Us navigation now leads to `/join`.

Frontend routes:

- `/join`: introduction, benefits, requirements, application steps, FAQ/help and three distinct actions.
- `/join/apply`: consented student lookup, limited self-confirmation preview and conditional application; no account creation.
- `/join/activate`: private, expiring officer invitation and strong password setup.
- `/member/login`, `/member/forgot-password`, `/member/reset-password`.
- `/member/dashboard`: actual member status/role, published official announcements and upcoming backend events. No invented activity.
- `/member/profile`: read-only student identity and verified contacts; biography, contact preference and private photo upload.
- `/member/settings`: password change and password-confirmed email change with a separate email-possession check.
- `/admin/members`, `/admin/members/applications`, `/admin/members/invitations`, `/admin/members/roles`, `/admin/members/audit`.

Backend `membership/` contains separate models, serializers, verification providers, permissions, services, API views/URLs, Django Admin, encryption and tests. `MUNCMember` has one-to-one relationships to the existing user and StudentIdentity. Seven seeded club roles are editable records, not authorization roles. The additional MemberAnnouncement model allows real official member notices through the protected Django Admin.

Models: StudentIdentity, MembershipApplication, MUNCMember, MembershipRole, ActivationInvitation, VerifiedContact, MembershipAuditLog and MemberAnnouncement. Identity registration numbers and optional student IDs are unique. Only one application and member claim may exist per identity. Relationships protect identity/audit history from accidental deletion. The StudentIdentity `verified_at` information belongs to the university **record check**; it never establishes the applicant's ownership of that identity.

## Permissions and officer onboarding

Super Admins can manage membership. Other administrators need staff status and Django `membership.manage_membership`. This explicit permission is recognized by the existing administrator login; membership-only officers enter the membership workspace without being granted Event Admin powers. Ordinary Event Admins and Reviewers receive no membership powers automatically. Club titles, including President, never grant staff/superuser privileges.

Create the first superuser using the existing password prompt:

```bash
cd Backend
source .venv/bin/activate
python manage.py createsuperuser
```

A Super Admin can use Django Admin → Users to designate an existing trusted staff administrator and assign the permission **“Manage club membership and independently confirm identity”**. Do not assign superuser merely to issue invitations. Do not give officers broad `auth.change_user` permission unless separately justified. Membership records and invitations are read-only in Django Admin; the React workflow/API enforces transitions. Club roles and official announcements can be authored in Django Admin by designated managers.

Officer workflow:

1. Review membership applications; mark under review, approved or rejected. Approval alone grants no account access.
2. Members → Create member → check the authorized student record. Independently inspect the intended student and record concise ownership evidence. This also supports authorized direct membership creation without an earlier application.
3. Choose an active club role. Enter an email only if its ownership has been independently confirmed; the application's self-reported email is not copied into trusted contacts.
4. Create an inactive member account with an unusable password.
5. Manage → record renewed identity confirmation → issue a verified-email invitation or deliver the private in-person link directly to the identified student. In-person delivery works without Brevo. Never publish it in a group chat or paste it into an audit note.
6. Invitations last 24 hours by default; a replacement requires a one-minute cooldown and revokes earlier unused invitations of that type. Raw links are not listed later. Revoke lost/compromised links; create a fresh invitation following renewed confirmation.
7. Member redeems the invitation, chooses a validated password and then logs in separately. Suspension/expiration revokes outstanding capabilities and existing sessions. Restoring previously activated membership does not revive old sessions.

There is no paid SMS integration or phone-based account claiming. VerifiedContact supports independently verified phone records, but no phone from a fee/payment record is imported or trusted. In-person delivery is the fallback when an independently verified email is unavailable.

## University/Sonali Bank integration: required manual configuration

Initially no authorized university/Sonali API adapter, endpoint contract or credentials were present. A later user-supplied official fee-page URL allowed inspection of its public single-record browser lookup; see the Sonali fee-page adapter section below. No endpoint was invented or bank/student records scraped. Production verification defaults to **disabled** and returns a generic service-unavailable message. A registration number cannot claim an account. The later requested confirmation flow intentionally previews the name, department and partially masked student ID after consent; it exposes no phone, email or membership/account status. This preview is not proof of identity ownership.

The reusable StudentVerificationService accepts a configured StudentVerificationProvider implementation. Obtain written university authorization and actual documentation first: endpoint/method, authentication/credentials, access restrictions, allowed request fields, documented response fields, rate limits, retention/consent requirements, provenance and permitted uses. Implement a reviewed server-side adapter returning `StudentRecord(registration_number, full_name, department, source, student_id='', session='')`. Use bounded authenticated requests, no redirects, generic sanitized exceptions and no provider payload logs. Do not return undocumented email/phone as trusted contacts. Configure the fully qualified adapter class as `MEMBERSHIP_VERIFICATION_PROVIDER=your_package.YourAuthorizedProvider` only after validation. Server configuration imports trusted Python code; users cannot supply adapter classes or expressions.

Local-only mock configuration supports **explicit synthetic fixtures**, never random successful student records. To try the complete UI locally, create this untracked temporary fixture (synthetic data only):

```bash
cat > /tmp/munc-membership-students.json <<'JSON'
{
  "DEMO-2026-001": {
    "full_name": "Development Student",
    "department": "Development Department",
    "student_id": "DEMO-ST-001",
    "session": "2026-27"
  }
}
JSON
```

In `Backend/.env`:

```dotenv
DEBUG=True
MEMBERSHIP_VERIFICATION_PROVIDER=mock
MEMBERSHIP_ALLOW_MOCK=True
MEMBERSHIP_MOCK_FIXTURE_FILE=/tmp/munc-membership-students.json
MEMBERSHIP_INVITATION_HOURS=24
```

Restart Django. Apply through `/join/apply` using the synthetic number. For production use `MEMBERSHIP_ALLOW_MOCK=False`, remove the fixture path and use `disabled` until the authorized adapter is reviewed/configured. Mock verification is blocked with DEBUG=False. Development fixtures must never be copied into a production membership database.

## Environment, local startup and email

No new production credentials are generated. Existing SECRET_KEY, PostgreSQL DATABASE_URL, session/CORS/CSRF origins, HTTPS/proxy configuration, Cloudinary credentials and Brevo configuration remain server-side. Frontend uses the existing VITE_API_BASE_URL or same-origin Netlify API proxy; no session/token secret is placed in localStorage.

New optional server settings:

| Variable | Default | Purpose |
| --- | --- | --- |
| MEMBERSHIP_VERIFICATION_PROVIDER | disabled | Authorized adapter class, explicit `sonali_bank` fee-page adapter, or development mock |
| MEMBERSHIP_ALLOW_MOCK | False | Development-only mock opt-in |
| MEMBERSHIP_MOCK_FIXTURE_FILE | empty | Local synthetic JSON fixture, maximum 1000 records |
| MEMBERSHIP_INVITATION_HOURS | 24 | Activation lifetime, 1–168 hours; recovery/email changes always one hour |

```bash
cd Backend
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py check
python manage.py runserver
```

In another terminal:

```bash
cd Frontend
npm ci
npm run dev
```

Email reuses the existing queue, quota/reserve, provider idempotency, suppression, webhooks and worker. Eight global editable membership templates are seeded. Global template editing remains Super Admin-only; security templates must retain the private URL in both bodies and cannot put it in the subject. Invitation/reset/email-verification jobs precede other transactional mail and campaigns. HTTP membership requests never call Brevo. Email being disabled/offline does not invalidate committed membership records; keep the queue worker running after configuring verified sender/API credentials, as described in DEPLOYMENT.md. A submitted application email is only an unverified receipt contact, not proof of ownership.

```bash
# Read-only diagnostic, never sends:
python manage.py process_email_queue --dry-run
# Actual sending, only when intentionally configured/enabled:
python manage.py email_worker
```

Invitation records store SHA-256 hashes of 256-bit random tokens, never plaintext tokens. Email bodies containing capabilities are encrypted at rest with standard Fernet, using an HKDF-separated key derived from the existing high-entropy Django SECRET_KEY. They are decrypted only inside the provider call. The added `cryptography` dependency (and cffi/pycparser) is justified by these private queued links; no new service is required. See the primary [Fernet documentation](https://cryptography.io/en/latest/fernet/). Keep SECRET_KEY stable while mail is pending; configured Django SECRET_KEY_FALLBACKS can decrypt mail made with an old key during a controlled rotation. Losing all relevant keys makes old queued links unrecoverable: revoke/reissue rather than weakening validation. Ordinary database dumps cannot read these encrypted queued links without server keys.

Links use URL fragments, not query strings, so the capability is not sent in proxy/request URLs. React removes the fragment from the current browser history entry after loading it, keeps it only in memory and submits it over the CSRF-protected API. Do not log request bodies or add third-party analytics/session replay to account pages. Invalid/expired/revoked invitations are skipped by the queue. An already in-flight message may arrive after revocation, but its capability cannot be redeemed. The existing queue retention command removes old terminal message content.

## APIs

All APIs are under `/api`. Unsafe methods require CSRF, including anonymous login, application and activation. Initialize CSRF through existing GET `/api/admin/auth/csrf/`; session cookies remain HttpOnly. Responses are private/no-store. Public sensitive actions and login/recovery identifiers have throttles, using the project's existing cache/fail-closed production rate-limit configuration. These quotas use the shared PostgreSQL limiter when Redis is absent; configured Redis remains optional. See RATE_LIMITING.md for backend selection, failure handling and cleanup.

| Endpoint | Methods / access |
| --- | --- |
| membership/lookup/ | POST public `{registration_number,consent}`; limited student preview and browser-bound, 10-minute signed lookup token |
| membership/apply/ | POST public `{registration_number,lookup_token,identity_confirmed,is_existing_member,contact_email,consent,motivation?,experience?}`; generic acknowledgement/reference |
| membership/activate/ | POST public `{token,password}` |
| membership/login/ | POST public `{identifier,password}`; registration or verified email |
| membership/logout/ | POST session logout |
| membership/password-reset/request/ | POST public `{identifier}`; generic response |
| membership/password-reset/confirm/ | POST public `{token,password}` |
| membership/me/ | GET/PATCH active account owner; PATCH biography/contact_preference only |
| membership/change-password/ | POST owner `{old_password,password}` |
| membership/change-email/ | POST owner `{email,password}`, then `{token}` after email possession |
| membership/photo/ | GET owner; POST multipart `photo`, PNG/JPEG <=2 MiB |
| membership/announcements/ | GET active member, published official notices |
| admin/student-verification/ | POST designated manager `{registration_number}` |
| admin/members/ | GET paginated/search/status; POST `{identity,role,identity_evidence,verified_email?}` |
| admin/members/{uuid}/ | GET manager; PATCH `{role}` |
| admin/members/{uuid}/photo/ | GET designated manager; authenticated image bytes only |
| admin/members/{uuid}/invite/ | POST `{identity_evidence,delivery_method}`; verified email or in_person |
| admin/members/{uuid}/suspend/, reactivate/, expire/, alumni/ | POST manager `{reason}` |
| admin/members/export/ | GET authorized CSV, formula-escaped and audited |
| admin/membership-applications/ | GET paginated/status/search |
| admin/membership-applications/{uuid}/approve/, reject/, under_review/ | POST manager decision |
| admin/membership-invitations/ | GET paginated safe metadata, no token/hash/private URL |
| admin/membership-invitations/{uuid}/revoke/ | POST revoke outstanding member capabilities of same purpose |
| admin/membership-roles/ | GET paginated / POST custom club role |
| admin/membership-roles/{id}/ | PATCH name/description/is_active |
| admin/membership-audit/ | GET manager, paginated, optional member UUID filter |

Membership ownership checks run on every protected request. Identity fields are rejected rather than silently changed. Different members cannot choose another member ID in an owner API. Photo bytes are validated, decoded/re-encoded, stripped of metadata and dimension-bounded, stored using the existing authenticated Cloudinary adapter in production, and streamed only through owner-authorized endpoints. Provider URLs are never returned. Production never stores these files on Heroku's ephemeral filesystem; local temporary private storage is development only. Current trusted contact values are unique across members. All private invitation delivery is an intentional manager action, not a public lookup.

Django session authentication is shared with the administration system. Signing into a different account in the same browser replaces the prior session; use separate browser profiles for simultaneous officer/member sessions. Password changes invalidate other authenticated sessions according to [Django authentication behavior](https://docs.djangoproject.com/en/5.2/topics/auth/default/). Use first-party routing through the existing reviewed Netlify proxy where possible; otherwise keep the existing explicit HTTPS credentialed CORS/CSRF/cookie configuration from AUTHENTICATION.md.

## Migrations and production readiness

New migrations: `mailing/0005_alter_emailmessage_event` permits non-event security mail; `membership/0001_initial` creates membership records/constraints; `membership/0002_seed_membership` seeds seven configurable club roles and eight global templates. No existing users, passwords, superusers, staff flags, events, submissions or historical content are replaced. No default member/admin credentials are created.

After a separately reviewed manual backend-only deployment, using your existing app:

```bash
MUNC_APP='your-existing-backend-app'
heroku run --app "$MUNC_APP" python manage.py migrate --noinput
heroku run --app "$MUNC_APP" python manage.py check
heroku config:set --app "$MUNC_APP" MEMBERSHIP_VERIFICATION_PROVIDER=disabled MEMBERSHIP_ALLOW_MOCK=False MEMBERSHIP_INVITATION_HOURS=24
```

Set the actual authorized adapter/credentials only after university authorization and review; no live Sonali verification is claimed. Keep DEBUG=False, actual HTTPS PUBLIC_SITE_URL/PUBLIC_API_URL and reviewed session/CSRF origins. Install the updated requirements on web and email-worker processes, and restart both. Do not scale paid workers or provision services automatically. Complete PostgreSQL activation concurrency testing against a **dedicated test database**, Cloudinary staging uploads and deliberate Brevo invitation/reset delivery tests before launch. No deployment or real membership email was sent during implementation.

## Verification commands

From Backend/:

```bash
DEBUG=True .venv/bin/python manage.py check
DEBUG=True .venv/bin/python manage.py makemigrations --check --dry-run
DEBUG=True .venv/bin/python manage.py migrate --noinput
DEBUG=True .venv/bin/python manage.py test --noinput
```

From Frontend/:

```bash
npm run lint
npm run test
npm run build
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome npm run test:e2e
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome python3 scripts/run-admin-integration.py
```

For another Chrome/Chromium installation, set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH to its installed binary, or install the Playwright browser. Real browser tests create only a temporary isolated SQLite database, synthetic student fixture, test accounts and private test photo; email transport is explicitly disabled. PostgreSQL-only row-lock tests are intentionally skipped under SQLite and must be run against a dedicated PostgreSQL test database before production concurrency claims.

Final local verification: Django checks/migrations/drift check passed; **160 backend tests run, 158 passed and 2 PostgreSQL concurrency tests skipped**. Frontend **46 tests**, lint and production build passed. Existing **4 browser regressions** and **7 real Django workflows** passed, including complete membership approval/private activation/login/profile/photo/suspension with responsive checks. Dependency consistency passed. Live university/Brevo/Cloudinary production behavior and PostgreSQL concurrency are not claimed by these local tests; the remaining manual configuration steps above still apply.


## Sonali fee-page adapter (user-supplied integration)

The official page https://billpay.sonalibank.com.bd/JKKNIU/SemesterFee/Honours was inspected directly. Its inline JavaScript uses POST `/JKKNIU/SemesterFee/GetStudent` with form field `id` uppercased and reads JSON `StudentId`, `Name`, `DeptName`, `ErrorMessage`. These names were observed, not invented. `membership/sonali.py` implements this exact single-entered-record flow using a fresh normal HTTP session and a GET of the supplied public page. It never posts the fee/payment form, follows redirects, bypasses CAPTCHA/authentication/security challenges, scans registration numbers or imports unrelated student records. Unexpected responses fail closed. Connections/read times, overall response processing and body size are bounded; raw upstream payloads/errors are not logged or returned.

Explicit server configuration:

```dotenv
MEMBERSHIP_VERIFICATION_PROVIDER=sonali_bank
MEMBERSHIP_ALLOW_MOCK=False
MEMBERSHIP_MOCK_FIXTURE_FILE=
```

The ignored local Backend/.env was updated to this provider at the user's request; restart Django to load it. No student lookup was performed with a real or guessed registration number during implementation. No new API key is assumed by this observed public-page flow. This is a browser-facing bank endpoint, not a documented/stable membership API or an assertion that institutional reuse permission has been granted. Obtain university/bank approval and a supported contract before production rollout; the example environment remains disabled by default. If the bank adds access restrictions, this adapter stops rather than attempting a workaround.

At `/admin/members` → Create member → Check authorized student record, designated officers can see registration number, student ID, name and department. Academic session is not invented; it remains absent unless a documented provider supplies it. Phone/email from payment forms are not trusted or imported. The public application endpoint still returns no personal identity record, and lookup success alone cannot activate an account. Use the student's real, consented registration number in the authorized admin workflow, never unrelated records.

The adapter has mocked contract, error, redirect, timeout, response-size, privacy and contact-provenance tests. End-to-end return values for a real student have not been verified because no student's registration number was supplied.


## Two-step student confirmation and membership declaration

The user requested an explicit public self-confirmation step after the Sonali lookup. `/join/apply` now first asks for the applicant's registration number and consent. **Show my student details** retrieves a limited preview (name, department and masked student ID) and asks **Is this you?**. The applicant can reject the record and check a different number. No email, phone or existing account/membership status is exposed by this lookup. Public preview necessarily reveals these limited student details to someone who supplies the number; it is rate-limited and audited and is not treated as identity ownership verification. Independent officer confirmation and private account activation remain required.

Step two requires **Yes, this is me**, an explicit **Are you already a MUNC member?** yes/no choice, email address and consent. Only new applicants see and must answer **Why would you like to join MUNC?** (20–5000 characters). Selecting existing membership suppresses and clears motivation; it is a self-reported declaration, never an authorization decision, approval or activation shortcut. Email is required for both choices but remains unverified for activation until independently confirmed.

Django validates a signed lookup receipt bound to the same browser session and registration number, expiring after ten minutes. A forged, expired or other-browser receipt cannot be submitted. Repeated submissions remain idempotent through the existing unique application identity; no duplicate emails or accounts are created. A fresh lookup is required after expiration or browser session rotation.

Migration membership/0003 adds self-declared membership and self-confirmation timestamps and permits blank motivation for existing members. Earlier applications retain their original motivation and an unknown declaration (`null`), rather than being falsely marked as having answered the new question. Admin application review shows the self-reported choice explicitly. No new account or student identity ownership is granted by this change.


The membership declaration now uses native, keyboard-accessible Yes/No radio choices instead of the dropdown. Switching to Yes clears hidden joining answers; changing the student record resets the declaration. Academic session has been removed from the public application preview and its lookup response; existing stored identity data remains intact.
