# Subdomain-based published sites

When `SITES_DOMAIN` is set (e.g. `sites.klarnow.com`), publishing a builder website uses a subdomain derived from the pack name instead of the path-based URL `/p/{project_id}`.

## Configuration

- **`SITES_DOMAIN`** (optional): The domain used for published sites. Example: `sites.klarnow.com`. When set, each published site gets a URL like `https://{pack-name-slug}.{SITES_DOMAIN}` (e.g. `https://acme-corp.sites.klarnow.com`).

## DNS and infrastructure

- **Wildcard DNS**: Point `*.{SITES_DOMAIN}` (e.g. `*.sites.klarnow.com`) to the same backend that serves the API. Requests to any subdomain must reach this app with the `Host` header unchanged so the app can resolve the project by subdomain.
- **TLS**: Use a wildcard certificate for `*.{SITES_DOMAIN}` (e.g. from Let’s Encrypt with DNS challenge) so all subdomains are served over HTTPS.

## Behavior

- **Publish**: On publish, the backend computes a URL-safe slug from the pack name, ensures uniqueness (e.g. `acme-2` if `acme` exists), stores it in `builder_project.subdomain_slug`, and sets `live_url` to `https://{subdomain_slug}.{SITES_DOMAIN}`.
- **Serving**: Requests to `https://{subdomain}.{SITES_DOMAIN}/` are handled by the subdomain router (GET `/`, POST `/lead`). The path-based URLs `https://{api_host}/p/{project_id}` and `/p/{project_id}/lead` continue to work when subdomain routing is not used (e.g. when `SITES_DOMAIN` is unset).
