# Shared database rate limiting

## Production fix and backend choice

The old login/public-registration throttles returned HTTP 503 whenever DEBUG=False and REDIS_URL was absent. They now share accounts/rate_limits.py. No authentication, password, user, superuser, CSRF, session or role model is replaced.

`RATE_LIMIT_BACKEND` supports:

- `auto` (default): use Redis when REDIS_URL is set, otherwise the existing database.
- `database`: always use the existing PostgreSQL database for these quotas.
- `redis`: require configured Redis and fail closed if it is missing or unavailable.

With PostgreSQL already provisioned and no REDIS_URL, no new production config variable or paid service is required. Keep DEBUG=False. To explicitly choose PostgreSQL, set RATE_LIMIT_BACKEND=database in the deployment environment. Do not set DEBUG=True to repair a production login failure.

Redis outages do not silently switch stores: resetting budgets mid-window would weaken limits. Redis's existing login/submission key formats, HMAC salts, periods and TTL behavior are retained. Switching backends deliberately starts new counters; perform such changes as a reviewed rollout. Production Redis mode rejects a process-local cache configuration. Other existing cache consumers remain unchanged.

## Limits and concurrency

Existing limits and identity handling remain unchanged:

- LOGIN_RATE_PER_MINUTE: default 10 per inferred IP/minute.
- LOGIN_RATE_PER_HOUR: default 100 per inferred IP/hour.
- LOGIN_USERNAME_RATE_PER_15_MINUTES: default 10 per normalized username/15 minutes.
- SUBMISSION_RATE_PER_MINUTE: default 5 per IP/minute.
- SUBMISSION_RATE_PER_HOUR: default 30 per IP/hour.
- SUBMISSION_EMAIL_RATE_PER_HOUR: default 5 per email/hour.
- Existing membership quotas use the same shared helper and retain their original values.

Both API login and Django Admin fallback login consume these limits. Successful and failed credentials consume quota; valid CSRF is still required. Excess requests receive 429 with Retry-After. Database/cache failures return the existing generic 503 and never proceed to an unthrottled login. Unknown accounts and invalid passwords still use generic authentication errors.

The new accounts.RateLimitCounter has a unique fixed-window key, internal scope, attempts and indexed expiration timestamp. Usernames, email addresses and IP addresses are HMAC-digested, not stored as plaintext identities. PostgreSQL determines the current window inside the same SQL statement as the atomic `INSERT ... ON CONFLICT DO UPDATE ... RETURNING`. Concurrent first inserts and later increments serialize on the unique bucket row across independent Gunicorn processes/dynos. There is no Python read/modify/write and no process-local production fallback. Attempts saturate at limit+1 to avoid unbounded counters. Backend locks/transaction commit happen before password verification on the login path.

See PostgreSQL's documented [atomic ON CONFLICT behavior](https://www.postgresql.org/docs/18/sql-insert.html). SQLite supports local development/testing through its equivalent UPSERT; production deployment checks require PostgreSQL when the database limiter is selected. Explicit transactions around callers retain their normal rollback semantics; limits remain enforced even if a rejected caller's transaction rolls back.

Fixed windows retain the pre-existing boundary behavior: a budget resets at its next clock boundary; this is not a sliding-window limiter. An expired/previous window's key cannot consume the next window's allowance. The database clock avoids discrepancies between web-worker clocks. Counters expire after the window end plus one period and five seconds, and are ignored by subsequent windows even before physical cleanup.

TRUSTED_PROXY_COUNT and DRF's client-IP selection are unchanged. Validate the real Netlify/Heroku forwarding chain separately; do not blindly increase trusted hops or trust arbitrary client-supplied forwarding headers.

## Migration and cleanup

Migration accounts/0002_ratelimitcounter creates only the new counter table/index. Existing user rows and credentials are untouched. Missing migrations fail closed; run migrations before the new web code accepts traffic. The existing Procfile release command already runs `python manage.py migrate --noinput`.

From the backend application's root:

```bash
python manage.py migrate --noinput
python manage.py check
python manage.py cleanup_rate_limits --dry-run
python manage.py cleanup_rate_limits --limit 10000
```

Cleanup uses the database clock, selects only expired keys, rechecks expiration on deletion and preserves active counters. Each run is bounded (default 10000 rows, maximum 100000); repeat if a backlog remains. Run regularly through an existing operations schedule or manual maintenance. This change does not provision Scheduler, cron, Redis, a worker dyno or any paid resource. A database cleanup error is generic and does not delete users or alter counters' admission logic. Expiry correctness does not depend on cleanup running, but periodic cleanup bounds storage.

## backend-heroku deployment preparation

This checkout is already on `backend-heroku`. Unlike the main branch's Backend/ layout, its Django files, requirements.txt, manage.py and Procfile are at the repository root. Make/review commits on this branch; do not subtree-split Backend again here, commit leftover Frontend artifacts, or add a Node buildpack.

Local verification from this branch root, using your activated Python environment and a development/dedicated test database:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py test --noinput
python manage.py cleanup_rate_limits --dry-run
```

For production-style concurrency tests, use a dedicated UTF-8 PostgreSQL database with permission to create/drop Django test databases. Never use a production DATABASE_URL for tests. Test settings/secrets belong in local server configuration, not Vite variables or Git.

When a separately reviewed deployment is authorized, deploy only backend-heroku using the project's existing Git/Heroku process. The release phase applies migrations; no deployment/push/config-var change was executed by this task. If checking migrations manually after that deployment:

```bash
MUNC_APP='your-existing-backend-app'
heroku run --app "$MUNC_APP" python manage.py showmigrations accounts
heroku run --app "$MUNC_APP" python manage.py check
heroku run --app "$MUNC_APP" python manage.py cleanup_rate_limits --dry-run
```

The accounts/0002 migration must show as applied. Then verify production login with CSRF, invalid-password generic errors, 429/Retry-After, logout/session status and the public registration flow. Do not create a new superuser or reset existing passwords for this fix. A continued 503 means inspect migration/database/selected-backend health; do not disable throttling.

## Testing and scope

Tests cover production DEBUG=False/no-Redis login, valid/invalid credentials, preserved superuser password/flags, CSRF rejection, IP minute/hour and normalized username limits, database failures, optional Redis selection/failure without budget reset, window rollover, capped counters, identity hashing, expiration cleanup/dry-run and exact concurrent quotas over separate PostgreSQL connections.

Two PostgreSQL concurrency tests specifically exercise simultaneous first inserts and later increments: 12 attempts against limit 5 admit exactly 5, and 8 public email attempts against limit 3 admit exactly 3. Full PostgreSQL validation also executes the existing queue-claim and account-activation concurrency tests. No real email, student lookup, Heroku deployment or production database operation is used.

The first full PostgreSQL run exposed test-harness issues previously hidden by SQLite: streaming responses were manually closed inside TestCase atomic transactions, the local test cluster initially used SQL_ASCII, and an older concurrency test assumed seeded roles survived database flushes. Tests now consume streaming content through Django's test client, the isolated test database uses UTF-8, and the concurrency fixture creates its own role. These are test fixes, not changes to production file access or membership behavior.

Final verification: Django checks and migration drift check passed; migrations were applied to isolated SQLite and PostgreSQL databases. The complete **182-test PostgreSQL suite passed with no skips**, including real concurrent login/submission quotas, existing email job claiming and activation redemption. SQLite ran **182 tests: 178 passed, 4 PostgreSQL-only tests skipped**. A production-style DEBUG=False/no-Redis deployment check reported no errors and only the two existing optional HSTS subdomain/preload warnings; no HTTPS settings were weakened. Cleanup dry-run succeeded. No live production login, deployment or Heroku configuration change is claimed.
