# Netlify API proxy

Root `netlify.toml` is the single source for redirects. It proxies `/api/*` to the configured Heroku backend before rewriting React routes to `/index.html`. The old `public/_redirects` SPA fallback has been removed: Netlify processes that file before TOML rules, so it would swallow API requests even when the TOML API rule came first. See [Netlify rule processing order](https://docs.netlify.com/manage/routing/redirects/overview/).

Existing build settings remain base `Frontend`, command `npm run build`, publish `dist`, Node 22. Security headers and asset/SVG caching rules are unchanged. No new caching rule is applied to API data; private Django responses retain their existing no-store policy.

## Production build and Netlify steps

- Commit/push the reviewed changes to the branch connected to Netlify, then trigger a new build. These local edits have not been deployed automatically.
- Retain the existing root `netlify.toml` configuration. Do not add another catch-all to `public/_redirects` or generate one during the build.
- Production uses the public setting `VITE_API_BASE_URL=/api`, defined in both root build environment and `Frontend/.env.production`. Review any existing Netlify dashboard/context environment overrides and remove an old localhost or direct Heroku API value. Set this variable to `/api` for production build context if managed through the dashboard. No API credentials belong in a VITE variable.
- Vite embeds environment values at build time, so changing an environment value requires a new build. `.env.production` also overrides the developer's generic `.env.local` during a normal production build. Shell/context overrides or `.env.production.local` can still override it; do not point those at localhost in production.
- The browser must call `https://jkkniu-munc.tech/api/...`; the Heroku hostname belongs only in the root proxy rule, not page components.

## Local development

```bash
cd Frontend
cp .env.example .env.local  # For first-time setup only; preserve an existing local file.
npm run dev
```

Local `.env.local` uses `VITE_API_BASE_URL=http://localhost:8000/api`. Run Django at `http://localhost:8000` and Vite at `http://localhost:5173`; use the same localhost hostname for cookie testing. No production backend URL is hardcoded in the client. The existing registration progress service still derives its endpoint from the shared `apiUrl` function; member photos now also use the central service rather than direct fetches in page components.

## Session authentication and CSRF compatibility

The existing client continues `credentials: include` for authenticated requests, JSON CSRF bootstrap, X-CSRFToken on writes and token refresh after login. Session secrets are never stored in localStorage. Private photo requests preserve credentials, abort signals, no-store and content-type validation. The public event submission service retains its existing anonymous upload behavior.

The Django code already supports host-only Secure/HttpOnly cookies and `AUTH_COOKIE_MODE=proxy` with SameSite=Lax. For a real deployment, the operator must confirm that its existing configuration trusts `https://jkkniu-munc.tech` in CSRF_TRUSTED_ORIGINS, permits the backend request hostname in ALLOWED_HOSTS, retains HTTPS proxy handling, and does not assign cookies to the Heroku domain. No Django/Heroku settings or credentials were changed by this task. If the backend still uses cross-site cookie mode, review its configuration separately rather than assuming a Netlify redirect changes Django settings.

Production login/logout, CSRF and session-cookie forwarding must be checked in a browser once both deployments are running. Local isolated integration tests do not prove live Netlify/Heroku cookie forwarding.

## Health verification

Read-only HTTP checks on 13 November 2026 returned:

| URL | Actual response before deployment of these changes |
| --- | --- |
| https://jkkniu-munc.tech/api/health/ | HTTP 200, text/html containing the React index page; not API health JSON |
| https://jkkniu-munc-api-d218cff97c80.herokuapp.com/api/health/ | HTTP 502, text/html with a Heroku welcome page; not API health JSON |

Both URLs therefore remain unverified as working APIs. Once the Django deployment is healthy and the updated frontend proxy is deployed, verify both:

```bash
curl --fail-with-body -i https://jkkniu-munc-api-d218cff97c80.herokuapp.com/api/health/
curl --fail-with-body -i https://jkkniu-munc.tech/api/health/
```

Both must return successful JSON `{"status":"ok"}`. A 200 HTML response is a failed proxy check, not success. The code's health endpoint returns this JSON without requiring authentication; a Heroku 502/welcome page needs separate backend deployment troubleshooting. This task makes no Heroku deployment changes.

## Local verification for this change

- TOML parsed successfully; the exact requested proxy and SPA rules are present once, in that order. Existing build directory/command/publish settings and all header values were compared and preserved.
- Vite production environment resolves to `/api`. Final built JavaScript contains neither the localhost development API base nor the Heroku hostname; no `_redirects` fallback is emitted into dist.
- Frontend lint and production build passed; **51 unit/component tests passed**. **7 isolated real Django browser workflows passed**, including session/CSRF login, membership/student confirmation/private profile photo, event forms, registration uploads, review/export, email administration and archive regressions. Live Netlify forwarding/session behavior remains unverified until deployment; current health results above are failures, not working API claims.
- Source changes: root netlify.toml; removed Frontend/public/_redirects; Frontend/.env.production, .env.example and .gitignore; central src/services/api.js and its tests; private-photo callers in src/pages/admin/MembersApp.jsx and src/pages/member/MemberPortal.jsx plus the member test mock; this guide and Backend/AUTHENTICATION.md. No backend application code, Heroku config vars, UI structure or event/archive content was changed.
