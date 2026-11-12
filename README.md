# JKKNIU MUNC API

Independent Django REST Framework backend. The existing React application stays on Netlify; nothing has been deployed. See [ARCHITECTURE.md](ARCHITECTURE.md) for the existing frontend and extension boundaries.

## Local startup

Run from the repository root (Python 3.14):

```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Paste the generated **local development** key into `SECRET_KEY` in `.env`; the example placeholder is intentionally rejected. No production secret is supplied by this project. Then:

```bash
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

`GET http://127.0.0.1:8000/api/health/` returns `{"status":"ok"}`. This is a liveness probe, not a database readiness check. POST/PUT/PATCH/DELETE are rejected. The backend does not serve the SPA.

The existing frontend can independently run with `cd Frontend && npm run dev` from the repository root. Its code still uses local data. Future frontend integration can call:

```js
fetch('http://127.0.0.1:8000/api/health/').then(response => response.json())
```

The API allows `http://localhost:5173` in development. Origins include scheme and port; add any other local origins explicitly. CORS does not authenticate users. Cross-origin cookies are disabled. Django admin uses same-origin session authentication and CSRF protection. A future Netlify authentication flow needs its own explicit design; no login/registration/submission endpoints are exposed yet.

## Event management

See [EVENT_API.md](EVENT_API.md) for models, staff authentication, filtering, request/response examples, and the explicit demo-data command. Events and multiple custom registration forms can also be managed in Django Admin.

## Environment

Process variables override `Backend/.env`. Comma-separated values are accepted for host/origin lists.

| Variable | Behavior |
| --- | --- |
| `DEBUG` | Defaults to false; true enables local defaults. Accepts true/false, yes/no, 1/0. |
| `SECRET_KEY` | Required; production rejects short, low-diversity and Django insecure-prefixed values. |
| `ALLOWED_HOSTS` | Explicit backend hostnames, without scheme; localhost defaults only in debug. Wildcard rejected. |
| `DATABASE_URL` | PostgreSQL connection URL; when supplied, always takes priority over SQLite. |
| `USE_SQLITE` | Defaults true; fallback permitted only in debug with no database URL. |
| `DATABASE_SSL_REQUIRE` | Defaults true in production, false in debug. Remove the example's local false override for Heroku. |
| `CORS_ALLOWED_ORIGINS` | Exact browser origins; localhost:5173 default only in debug. |
| `CSRF_TRUSTED_ORIGINS` | Exact trusted origins for CSRF; localhost:5173 default only in debug. Does not bypass CSRF token checks. |

Production requires a key, explicit allowed hosts and PostgreSQL. HTTPS redirect, secure session/CSRF cookies and one-year HSTS are enabled with `DEBUG=False`. Subdomain HSTS and preload remain disabled pending a domain-wide decision. `X-Forwarded-Proto` is trusted for Heroku's router; run behind a trusted proxy. Timestamps are timezone aware (`USE_TZ=True`), stored as UTC by Django, with Asia/Dhaka as the application timezone.

## Heroku preparation (no deployment performed)

Heroku must receive **the contents of Backend as its application root**, with `requirements.txt`, `.python-version` and `Procfile` at that root. Do not deploy the repository root or add a Node buildpack. For a future Git-based deployment, commit the backend and export the `Backend` subtree to a separate branch/repository (for example, `git subtree split --prefix Backend -b backend-heroku`); send only that branch to the backend Heroku application when deployment is authorized. Do not run deployment commands as part of local setup.

Provision PostgreSQL separately when ready and configure `DATABASE_URL`, a securely managed production `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=<exact-backend-host>`, `CORS_ALLOWED_ORIGINS=https://<actual-netlify-or-custom-domain>`, and the appropriate `CSRF_TRUSTED_ORIGINS` using actual HTTPS origins. Never use broad `*.netlify.app` allowances. Leave `DATABASE_SSL_REQUIRE` unset or true. No real domains or credentials are assumed here.

Heroku's Python buildpack installs the pinned requirements and runs Django static collection. WhiteNoise serves backend/admin static files, not frontend assets. The Procfile release phase applies migrations; the web phase starts Gunicorn on `$PORT`. Database failures stop the release. Do not store persistent data or uploads on Heroku's ephemeral filesystem. No upload feature or paid service integration has been added.

Before a future release, run `python manage.py check --deploy` with the actual production environment and review pending migrations. The health probe does not confirm database availability. Set up platform logging, backups and monitoring when infrastructure is provisioned.

References: [Heroku Python setup](https://devcenter.heroku.com/articles/getting-started-with-python), [Procfile](https://devcenter.heroku.com/articles/procfile), [Django security settings](https://docs.djangoproject.com/en/5.2/ref/settings/).

## Validation

With local `.env` configured:

```bash
python -m pip check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test --verbosity 2
python manage.py collectstatic --noinput
```

The tests cover public health access without a database query, method restrictions, allowed/disallowed CORS, HTTPS proxy handling, app registration, aware timestamps, an auth database round trip, and isolated environment configuration. PostgreSQL configuration is tested without connecting. Live PostgreSQL and Heroku integration require infrastructure and are not validated locally.
