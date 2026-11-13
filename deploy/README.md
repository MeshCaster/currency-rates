# Deploying Currency Rates

Production runs on the CONTABO VPS as three containers on the `meshcaster` network, deployed by
[`.github/workflows/production.yml`](../.github/workflows/production.yml) on every push to `main`
through MeshCaster/DevOps's reusable `deploy-container.yml`. None publishes a host port. The
public app is reached through the shared nginx proxy, behind a Cloudflare-proxied DNS record; the
admin app only through the Cloudflare tunnel, with Cloudflare Access in front.

| Container | Image | Port | What it is |
|---|---|---|---|
| `currency-rates-api` | `currency-rates` (`APP_ROLE=api`) | 8000 | FastAPI; runs `alembic upgrade head` before it starts |
| `currency-rates-worker` | `currency-rates` (`APP_ROLE=worker`) | — | Sync, alert and email jobs; seeds the provider catalog and first admin |
| `currency-rates-web` | `currency-rates-web` | 8080, 8081 | Public app (8080) and admin app (8081, which also routes `/api/` to the API) |

| | |
|---|---|
| Database | `meshcaster_currency_rates` on the shared `meshcaster-postgres` |
| Env file | `/opt/meshcaster/currency-rates.env` (API and worker) |
| Public app | `https://currency-rates.in-vent.online` (`/api/` → API) |
| Admin app | `https://currency-rates-admin.in-vent.online`: tunnel → `currency-rates-web:8081`, Cloudflare Access |
| vhost | [`nginx/currency-rates.conf`](nginx/currency-rates.conf) (public app only) |

## First deploy

1. **DNS:** a proxied A record for `currency-rates.in-vent.online` → the VPS. The admin hostname
   gets its record from the tunnel in step 4.

2. **On the server**, create the database and the env file:

   ```bash
   scp deploy/bootstrap-env.sh contabo:/tmp/
   ssh contabo 'bash /tmp/bootstrap-env.sh you@example.com'
   ```

   Save the admin password it prints; it is not stored anywhere else. Add the `SMTP__*` values to
   the env file when you have a mail provider.

3. **Certificates and vhost**, from a checkout of MeshCaster/DevOps:

   ```bash
   tools/nginx/remote-setup.sh -i ~/.ssh/meshcaster_contabo_vps_1 root@169.58.27.99 \
     --skip-init --email you@example.com \
     --cert "currency-rates.in-vent.online" \
     --conf ../PycharmProjects/currency-rates/deploy/nginx/currency-rates.conf
   ```

4. **Admin app through the tunnel**, in Cloudflare Zero Trust:
   - **Networks → Tunnels →** the existing tunnel **→ Public Hostname → Add**:
     `currency-rates-admin.in-vent.online` → `HTTP` → `currency-rates-web:8081`.
   - **Access → Applications → Add → Self-hosted** for the same hostname, with a policy that
     allows the emails who may open it (e.g. the interviewers'). Cloudflare then asks for a
     one-time code sent to that email before the admin app loads.

5. **Repository secrets:** `CONTABO_HOST`, `CONTABO_USERNAME`, `CONTABO_SSH_PRIVATE_KEY`.

6. **Run "Deploy to production"** (Actions tab, or push to `main`).

## Operating it

- **Logs:** `ssh contabo docker logs --tail 100 currency-rates-api` (or `-worker`, `-web`).
- **Migrations** ship with the API image and run when it starts. To run one by hand:
  `docker run --rm --network meshcaster --env-file /opt/meshcaster/currency-rates.env ghcr.io/meshcaster/currency-rates alembic current`.
- **Rollback:** every deploy also pushes `:<commit sha>`; re-run an older workflow run, or
  `docker run` that tag with the same flags.
- **Other hostnames:** change them in the vhost and pass `SITE_HOST` / `ADMIN_HOST` to
  `bootstrap-env.sh` (or edit `SECURITY__ALLOWED_HOSTS` in the env file).
