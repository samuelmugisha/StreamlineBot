# Deployment

## Where this runs

Production is deployed on **DigitalOcean App Platform**
(`https://coral-app-cwkpt.ondigitalocean.app`) as two components built from
this repo's Dockerfiles: the API (`Dockerfile`) and the widget
(`frontend/Dockerfile`).

## Recommended path: DO App Platform's native GitHub auto-deploy

If the App Platform app is already connected to this GitHub repo (Settings
→ App → App-Level Environment Variables / the component's source), App
Platform rebuilds and redeploys automatically on every push to `main` —
nothing in `.github/workflows/` is required for this to work. This is the
simplest option and is very likely how this app is already configured.

To confirm/enable it: DigitalOcean dashboard → your app → **Settings** →
each component → **Source** → check "Autodeploy" is on for the `main`
branch.

## Optional: gate deploys behind this repo's CI

`.github/workflows/cd.yml` builds and pushes Docker images to GitHub
Container Registry (GHCR) on every push to `main`, tagged with both the git
SHA and `latest`. This is useful even without wiring up the `deploy` job —
it gives you an auditable, versioned image history independent of DO's own
build.

If you want this workflow to *also* trigger the DO deployment (e.g. so a
failing CI run blocks deploy, or so you can drive deploys from GitHub
Actions instead of DO's dashboard):

1. In DigitalOcean: **API** → **Generate New Token** (read/write scope)
2. In this repo: **Settings → Secrets and variables → Actions**:
   - Add secret `DIGITALOCEAN_ACCESS_TOKEN` — the token from step 1
   - Add secret `DO_APP_ID` — found in the app's URL or via `doctl apps list`
   - Add **variable** `ENABLE_DOCTL_DEPLOY` = `true`
3. Optionally add variable `VITE_API_URL` (the public API URL) so the
   widget image is built pointing at the right backend.

With `ENABLE_DOCTL_DEPLOY` unset or `false`, the `deploy` job is skipped
entirely and DO's own auto-deploy (if enabled) is what ships changes — the
two mechanisms don't conflict, but running both means the DO deploy could
win the race. Pick one.

## Manual deploy (fallback)

```bash
# Build and push manually
docker build -t <registry>/streamline-bot-api:latest -f Dockerfile .
docker push <registry>/streamline-bot-api:latest

docker build -t <registry>/streamline-bot-widget:latest \
  --build-arg VITE_API_URL=https://coral-app-cwkpt.ondigitalocean.app/api \
  -f frontend/Dockerfile ./frontend
docker push <registry>/streamline-bot-widget:latest
```

Then trigger a deploy from the DO dashboard, or:
```bash
doctl apps create-deployment <DO_APP_ID> --wait
```

## Environment variables

Set production values for everything in `.env.example` as DigitalOcean App
Platform **encrypted** environment variables (never commit `.env`). See the
table in `README.md` for what each one does. At minimum, before first
deploy:

- `API_KEY` — required, or every endpoint is public
- `ALLOWED_ORIGINS` — must include the exact origin(s) the widget is embedded on
- `GOOGLE_AI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — required at startup, the app refuses to boot without them
- `SENTRY_DSN` / `VITE_SENTRY_DSN` — optional, enables error tracking

## Database migrations

Supabase schema changes are plain SQL files in `backend/db/`. There is no
migration runner — apply new `migration_*.sql` files manually via the
Supabase SQL Editor (see `README.md`'s Setup section for the ordering
caveat around `schema.sql`'s `drop table`).

## Rollback

- **DO App Platform**: dashboard → app → **Activity** → pick a previous
  successful deployment → **Rollback**. This reverts the running
  containers immediately; it does not revert any database migration.
- **GHCR images**: every image is tagged with its git SHA
  (`ghcr.io/<repo>-api:<sha>`), so a specific previous build can always be
  redeployed manually even if DO's rollback history has rotated it out.
- Database changes are additive-only by convention (see the `migration_*.sql`
  files) specifically so that a code rollback doesn't require an undo of the
  schema.

## Post-deploy smoke check

```bash
curl https://coral-app-cwkpt.ondigitalocean.app/api/health
# {"status":"ok","version":"1.0.0"}
```

Then verify one real `/chat` round trip and one `/history/{session_id}`
call with a valid API key before considering the deploy verified — see
`docs/RUNBOOK.md`.
