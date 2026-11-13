# Brevo email management: setup and operations

This feature is implemented but **not deployed or enabled**. No real email was sent, no provider account was created and no paid service was provisioned. Frontend hosting remains Netlify; deploy only the existing `Backend/` application to Heroku using your reviewed backend-only deployment workflow. Retain the existing PostgreSQL, session/CSRF, CORS, private storage and proxy settings described in README.md and AUTHENTICATION.md.

## 1. Brevo account, sender and DNS

1. Create/sign into the club's Brevo account. Check that transactional sending is activated, the account's actual daily allowance and whether authenticated transactional webhooks are available on its plan.
2. Add the club's sender address and display name. Complete Brevo's sender verification. Use a domain the club controls, rather than personal Gmail SMTP.
3. Add/authenticate the domain in Brevo. Copy the exact Brevo-code and DKIM TXT/CNAME records shown for this account into its DNS provider. Follow the account's return-path/SPF instructions if shown; never guess a universal SPF value or add a second SPF record. Preserve existing authorized senders when merging SPF changes. Add/update the single DMARC policy at `_dmarc`; do not blindly replace an existing policy with a weaker example. Confirm authentication in Brevo before sending. The current/legacy authentication flows can differ; use [Brevo's domain setup](https://help.brevo.com/hc/en-us/articles/35337929909778-Set-up-your-domain-in-Brevo) and [domain authentication guide](https://help.brevo.com/hc/en-us/articles/12163873383186-Authenticate-your-domain-with-Brevo-Brevo-code-DKIM-DMARC).
4. Generate a transactional API key in Brevo and keep it in server-side secrets. Use a separate high-entropy secret from your secret manager for webhook authentication. Neither value belongs in Vite variables, Git, screenshots or provider error logs.

## 2. Backend configuration

All values below are environment variables. `.env.example` contains development examples and empty secret slots. The safe default is `EMAIL_ENABLED=False`. No production secret has been generated.

| Variable | Default / purpose |
| --- | --- |
| `EMAIL_ENABLED` | `False`; explicitly enable after setup |
| `EMAIL_PROVIDER` | `brevo` |
| `BREVO_API_KEY` | Required for transport; secret |
| `BREVO_WEBHOOK_TOKEN` | Separate secret, required to accept webhooks |
| `DEFAULT_FROM_EMAIL` | Verified Brevo sender; no default address |
| `DEFAULT_FROM_NAME` | `JKKNIU Model United Nations Club` |
| `PUBLIC_SITE_URL` | Official Netlify/custom HTTPS site origin in production |
| `PUBLIC_API_URL` | Public HTTPS API base including `/api`; can use the same-origin Netlify API proxy |
| `EMAIL_DAILY_LIMIT` | `300`; align with actual account allowance and other senders |
| `EMAIL_TRANSACTIONAL_RESERVE` | `50`; bulk/test jobs cannot consume this reserved capacity |
| `EMAIL_RATE_PER_MINUTE` | `60`; database-enforced across workers |
| `EMAIL_CONNECT_TIMEOUT` / `EMAIL_READ_TIMEOUT` | `5` / `20` seconds |
| `EMAIL_MAX_ATTEMPTS` | `5`; bounded automatic attempts for known retryable failures |
| `EMAIL_RETRY_BASE_SECONDS` | `60`; exponential backoff, capped at one day and respecting Retry-After |
| `EMAIL_LEASE_SECONDS` | `180`; must exceed both timeouts plus 30 seconds |
| `EMAIL_QUOTA_TIME_ZONE` | `UTC`; confirm/reset alignment against your Brevo account |
| `EMAIL_RETENTION_DAYS` | `180`; terminal message-content redaction |
| `EMAIL_CAMPAIGN_MAX_RECIPIENTS` | `10000`; snapshots also capped at 20 MiB of rendered content |

In development, URL defaults are `http://localhost:5173` and `http://localhost:8000/api`. Production public URLs must be absolute HTTPS URLs without credentials, query or fragment. The operator must configure the actual public origins; no Heroku hostname is hardcoded.

The local quota is conservative and approximate: reserved requests consume a slot even if a response fails or is uncertain. It cannot see mail sent directly through another Brevo integration. Keep headroom and monitor Brevo's actual account quota. The daily allowance is configurable, not a promise about an account's current plan. See [Brevo plan limits](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan).

## 3. Exact local commands

From the repository root:

```bash
cd Backend
source .venv/bin/activate
DEBUG=True python manage.py migrate --noinput
DEBUG=True python manage.py check
DEBUG=True python manage.py makemigrations --check --dry-run
DEBUG=True python manage.py test --noinput
DEBUG=True python manage.py process_email_queue --limit 25 --dry-run
DEBUG=True python manage.py runserver
```

In a second terminal:

```bash
cd Frontend
npm ci
npm run lint
npm run test
npm run build
npm run dev
```

Use the existing private frontend `.env.local` with `VITE_API_BASE_URL=http://localhost:8000/api`, or the reviewed `/api` proxy setup. Open `/admin/email`; `/admin/email-campaigns` redirects to Campaigns. Only Super Admins and assigned Event Admins can send/manage email. Reviewers can see an assigned applicant's email/payment summary but cannot send campaigns, change templates, or verify money.

Before intentionally sending anything locally, configure a verified sender/key and set `EMAIL_ENABLED=True` in the **backend** environment. Then an authorized operator can run:

```bash
DEBUG=True python manage.py process_email_queue --limit 5 --transactional-only
DEBUG=True python manage.py process_email_queue --limit 25
# Alternative continuous local worker; stop with Ctrl+C:
DEBUG=True python manage.py email_worker
```

The worker sends real mail when enabled. `--dry-run` never claims jobs, creates recipient snapshots or contacts the provider. Preview is local rendering; Send test creates a durable job targeting only the signed-in administrator's account email. It does not claim successful delivery. Staff account email addresses are managed by Super Admins; no independent recipient-ownership verification flow was added.

## 4. Exact Heroku configuration (manual, not executed)

Use your existing backend app, with reviewed deployment artifacts rooted in `Backend/`. Do not deploy Frontend/ to Heroku. Set the real identifiers below locally before running commands:

```bash
MUNC_APP='your-existing-backend-app'
MUNC_SITE='https://your-official-site.example'
MUNC_PUBLIC_API='https://your-public-backend.example/api'
MUNC_SENDER='verified-sender@your-domain.example'
heroku config:set --app "$MUNC_APP" \
  EMAIL_ENABLED=False EMAIL_PROVIDER=brevo \
  DEFAULT_FROM_EMAIL="$MUNC_SENDER" \
  DEFAULT_FROM_NAME='JKKNIU Model United Nations Club' \
  PUBLIC_SITE_URL="$MUNC_SITE" PUBLIC_API_URL="$MUNC_PUBLIC_API" \
  EMAIL_DAILY_LIMIT=300 EMAIL_TRANSACTIONAL_RESERVE=50 \
  EMAIL_RATE_PER_MINUTE=60 EMAIL_CONNECT_TIMEOUT=5 EMAIL_READ_TIMEOUT=20 \
  EMAIL_MAX_ATTEMPTS=5 EMAIL_RETRY_BASE_SECONDS=60 EMAIL_LEASE_SECONDS=180 \
  EMAIL_QUOTA_TIME_ZONE=UTC EMAIL_RETENTION_DAYS=180
```

Prefer entering secrets directly in Heroku Dashboard → Settings → Config Vars. If using a terminal, avoid literal secrets in shell history/output:

```bash
read -r -s -p 'Brevo API key: ' MUNC_BREVO_KEY
heroku config:set --app "$MUNC_APP" BREVO_API_KEY="$MUNC_BREVO_KEY" >/dev/null
unset MUNC_BREVO_KEY
read -r -s -p 'Webhook bearer secret: ' MUNC_WEBHOOK_SECRET
heroku config:set --app "$MUNC_APP" BREVO_WEBHOOK_TOKEN="$MUNC_WEBHOOK_SECRET" >/dev/null
unset MUNC_WEBHOOK_SECRET
```

After the **separately reviewed manual backend deployment**, the existing release phase applies migrations. Verify explicitly:

```bash
heroku run --app "$MUNC_APP" python manage.py migrate --noinput
heroku run --app "$MUNC_APP" python manage.py check
heroku run --app "$MUNC_APP" python manage.py process_email_queue --limit 5 --dry-run
```

Do not run Django tests against a production database/credential. Use a dedicated PostgreSQL test database for the parallel-worker test.

### Option A: Heroku Scheduler

[Heroku Scheduler](https://devcenter.heroku.com/articles/scheduler) has a free add-on installation, but its one-off dynos consume billable usage. Jobs may be missed or duplicated; installing the add-on does not guarantee delivery. No Scheduler add-on was installed here.

Only after cost approval, a human operator may run:

```bash
heroku addons:create scheduler:standard --app "$MUNC_APP"
heroku addons:open scheduler --app "$MUNC_APP"
```

Add a job at an appropriate frequency (for example, every 10 minutes):

```text
python manage.py process_email_queue --limit 25
```

A separate transactional-only job can prioritize urgent confirmations:

```text
python manage.py process_email_queue --limit 25 --transactional-only
```

The database queue survives missed runs and idempotent claiming handles overlapping invocations. The worker records last activity; monitor overdue jobs and uncertain leases. Quota-blocked jobs remain pending and become eligible on the next configured quota day; no operator reset is needed. The command caps each batch run at approximately five minutes, plus the current provider request. Required throughput and timeliness must be evaluated against actual Scheduler frequency/usage.

### Option B: dedicated worker

For tighter delivery latency and continuous reconciliation, the Procfile defines `emailworker: python manage.py email_worker`. It remains a deployment option, not a provisioned service. A dedicated worker dyno has ongoing cost; scale it only after funding approval:

```bash
heroku ps:scale emailworker=1 --app "$MUNC_APP"
# Stop paid continuous execution when appropriate:
heroku ps:scale emailworker=0 --app "$MUNC_APP"
```

Multiple workers use PostgreSQL row locks, per-job state and a shared database quota/rate gate. Run the included PostgreSQL concurrency test before scaling beyond one worker. SQLite is for local **single-worker** use only. No Celery or new Redis service is introduced; the pre-existing project's cache/rate-limit configuration remains separate.

## 5. Brevo webhook configuration

Brevo documents [bearer authentication for webhooks](https://developers.brevo.com/docs/secured-webhooks). Configure a transactional webhook targeting:

```text
PUBLIC_API_URL/webhooks/brevo/
```

For example, if `PUBLIC_API_URL=https://api.example/api`, the webhook URL is `https://api.example/api/webhooks/brevo/`. Set its authentication to Bearer using the **separate** `BREVO_WEBHOOK_TOKEN`. Do not send the Brevo API key as the webhook token and do not put credentials in the URL.

Use Brevo Dashboard if it exposes authenticated webhooks for your account, otherwise run this **manually**, in a secure environment containing the actual server environment variables:

```python
import os
import requests
response = requests.post(
    'https://api.brevo.com/v3/webhooks',
    headers={'api-key': os.environ['BREVO_API_KEY']},
    json={
        'description': 'JKKNIU MUNC transactional delivery',
        'url': os.environ['PUBLIC_API_URL'].rstrip('/') + '/webhooks/brevo/',
        'type': 'transactional',
        'events': ['request', 'delivered', 'deferred', 'softBounce',
                   'hardBounce', 'blocked', 'invalid', 'error', 'unsubscribed'],
        'auth': {'type': 'bearer', 'token': os.environ['BREVO_WEBHOOK_TOKEN']},
    },
    timeout=(5, 20),
)
print('Webhook configuration HTTP status:', response.status_code)
response.raise_for_status()
```

Inspect existing webhooks first to avoid configuring duplicate deliveries. The endpoint handles duplicate events idempotently, normalizes message IDs and supports opaque custom correlation when a callback arrives before the send response. It requires the event recipient to match the stored job. Earlier deferrals cannot undo confirmed delivery. Raw webhook bodies, applicant addresses and provider credentials are not copied to attempt/error logs.

Events and payload names follow [Brevo's transactional webhook reference](https://developers.brevo.com/docs/transactional-webhooks). No valid authenticated delivery webhook means **accepted**, not **delivered**. Hard-bounce/invalid/spam/blocked addresses are suppressed before later claims. Provider deferrals and soft bounces do not trigger duplicate application-level sends.

## 6. Test-email procedure and enabling

1. Keep transport disabled initially. Sign in as an authorized administrator whose account email is correct.
2. Open Email management → Templates; preview an approved template with example data.
3. Create a draft campaign for an assigned test event, inspect unique-recipient count, classification, and personalized preview. Never use a real applicant list for an initial transport test.
4. Click **Send test to my admin email**. This queues one job; it cannot target an arbitrary client-supplied address. Network retries in the same editor reuse its request UUID.
5. After sender/DNS verification, webhook setup, quota review and worker funding decisions, explicitly enable transport:

```bash
heroku config:set EMAIL_ENABLED=True --app "$MUNC_APP"
heroku run --app "$MUNC_APP" python manage.py process_email_queue --limit 1
```

This processes the highest-priority due job, which may be a queued applicant confirmation rather than the test if a backlog exists. Review pending jobs first. Use a dedicated staging app/database with your own test registrations for the first real provider check.

6. Confirm HTTP acceptance/message ID in Delivery history, then **separately** confirm the inbox and authenticated delivered webhook. Check message headers for DKIM/DMARC/SPF results. A test hitting an inbox does not prove all recipients will receive mail.
7. Review per-event automatic settings and next instructions before allowing new campaigns. Event reminders and EB interview invitations use the corresponding editable templates with the same schedule/classification/recipient controls; no hardcoded registration categories are required.

## 7. Monitoring, uncertainty and retries

- Watch Email Overview (pending/failed/unknown counts, approximate quota, last worker activity), campaign progress, Delivery history, Failed/uncertain, Heroku job exits and Brevo's logs.
- Queued/sending/accepted/delivered have different meanings. A completed campaign means all jobs have left active/uncertain processing, not that all were delivered. Per-message results remain visible.
- Registration hooks queue only after commit and never call Brevo in HTTP submission/status/payment requests. A callback insertion failure is caught without undoing a saved registration; the next enabled worker reconciles missing jobs from authoritative submission/status/payment records. A migration-time cutover prevents unsolicited confirmation backfill to registrations predating this feature.
- Automatic event settings are checked at queue creation and again before claiming. Re-enabling a skipped historical transition does not silently resend it. Templates are copied into each job, so editing a template cannot corrupt or change a queued request.
- Known connection-establishment timeouts and HTTP 429 responses use bounded backoff. Provider acceptance, response timeouts, network disconnects, malformed successful receipts, ambiguous server errors and duplicate idempotency responses are never blindly resent. Expired worker leases become uncertain.
- Brevo's documented [idempotency window is 30 minutes](https://developers.brevo.com/docs/heterogenous-versions-batch-emails). The UUID and frozen headers are reused, but the app does **not** claim indefinite exactly-once provider delivery. Uncertain jobs remain on hold beyond that window.
- For an uncertain job, check Brevo's original logs. An authorized manager can record the original accepted provider ID, or cancel unresolved processing. This does not send another email or falsely mark delivery. If an operator establishes that a separate follow-up is necessary, use a new explicitly reviewed campaign rather than an automatic retry of an uncertain request.
- Known failed/retryable jobs can be explicitly retried after their automatic attempt budget is exhausted. Attempts remain monotonic and audited. Completed campaigns can reopen only for their failed job; accepted recipients are never included in that retry. Paused/cancelled campaigns do not silently send.
- Pause/cancel stops unclaimed campaign jobs. A job already claimed by a worker may finish; accepted messages cannot be recalled. Neither a screenshot nor an application approval verifies payment.
- If quotas or credentials are wrong, keep transport disabled or pause campaigns. Do not bypass quota counters to clear a backlog. Budget for other senders using the same Brevo account and align `EMAIL_QUOTA_TIME_ZONE` with the account's reset window.

## 8. Consent, retention and security

Optional marketing requires an explicit EmailPreference opt-in with evidence/recording actor; data-processing consent does not grant marketing permission. Recipient snapshots exclude suppressed/nonconsenting addresses, and preferences are checked again immediately before claim. Public unsubscribe capability links contain a signed preference identifier, not an email address; GET shows a confirmation and POST opts out. Optional opt-out does not disable necessary operational application notices. Operators must classify messages truthfully and keep operational campaigns limited to legitimate updates for that event.

Message content contains only approved variables; there is no Django template/eval execution, attachment injection, private file variable or client-side provider credential. HTML uses a strict allowlist; source/personalization is sanitized/escaped. Preview iframes have no script/same-origin/resource permissions. Test and campaign messages have one To recipient, never a shared recipient list. Existing Django sessions, CSRF, explicit origins and event assignments protect administrative actions. Email actions and payment transitions have actor audits.

Run retention periodically, reviewing a dry run first:

```bash
python manage.py purge_email_history --dry-run
python manage.py purge_email_history
```

After `EMAIL_RETENTION_DAYS`, terminal job recipients, bodies, headers and subject/error content are redacted. Opaque event keys, minimal delivery timestamps/attempt outcomes and source IDs remain as idempotency/audit tombstones. Uncertain jobs are held for manual reconciliation, not erased into an accidental resend. Minimal consent/unsubscribe/suppression records are retained so opt-outs and hard-bounce protection remain enforceable. Templates, original application records, payment ledgers and provider-side Brevo logs have separate retention responsibilities; this command is not a claim to delete every copy of applicant information. Do not log full unsubscribe URLs or campaign bodies.

## 9. Tests and remaining manual checks

See EMAIL_SYSTEM.md for the file/API manifest and local validation report. Provider calls are mocked in automated tests. The browser runner explicitly disables transport, creates disposable accounts/database/private files, queues an administrator-only test job and never sends it. Live Brevo account approval, sender/DNS verification, actual webhooks/delivery, Heroku/Netlify routing and funded worker scheduling require manual setup. PostgreSQL parallel claiming is included as a conditional automated test but cannot run against SQLite.

On a **dedicated PostgreSQL test environment** with permission to create a test database:

```bash
python manage.py test mailing.tests.CommitTests.test_parallel_workers_claim_each_job_once
```

No deployment, real email, account provisioning or paid scaling is performed by these instructions themselves.

## Membership readiness

See [MEMBERSHIP.md](MEMBERSHIP.md) for migration commands, designated-officer onboarding, student-provider authorization, private activation, mock fixtures and security testing. Install the updated requirements on web and email workers. Keep university verification disabled until actual authorized Sonali/university API documentation and credentials are available. No endpoint was guessed and no student records were scraped. Activation/reset links waiting in the email queue are encrypted with a domain-separated key derived from Django SECRET_KEY; manage key rotation deliberately. First-party session routing, Cloudinary authenticated storage and Brevo remain the existing infrastructure; no SMS service is required.
