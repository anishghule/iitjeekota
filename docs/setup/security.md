# Security: what is in place and what you do

Rules: `CLAUDE.md` section 5. Design: `docs/adr/0009-security-headers-and-supply-chain.md`. You carry out the steps below; nobody needs to share a login with Claude.

## In the repository now

| What | Where | Checked by |
|---|---|---|
| Content Security Policy and the other response headers | `packages/site/security.json`, written to `_headers` by `make web-data` | `make site`, the unit tests and `apps/web/e2e/security.spec.ts`, which loads real pages under the exact policy |
| Real 301 from `/` to `/en/` | `_redirects`, from `packages/site/site.json` | `make web-data` |
| `/.well-known/security.txt` | `securityTxt` in `security.json`; the contact is the confirmed `contact.email` fact | `make site` fails when it has expired |
| Nothing loads from another site, no inline scripts, styles or event handlers | `make web-lint` on the built pages | `make check` |
| Hidden data removed from every image and video | `images/scrub.py`, `make media-encode` | `make web-lint` reads the shipped files |
| Exact, hash-locked dependencies at least 14 days old | `pnpm-workspace.yaml`, `renovate.json`, `tools/ci/requirements.txt` | `make js-install`, Renovate |
| ruff and bandit on the tooling, `pnpm audit` on what the site ships | `make security` | CI |
| gitleaks, OSV-Scanner, `pip-audit` of the CI tools, software bill of materials | `.github/workflows/ci.yml`, `.gitleaks.toml`, `osv-scanner.toml` | CI on every push and pull request |
| Semgrep | Deferred: its newest eligible release pins vulnerable packages (ADR 0009) | Not run |
| OWASP ZAP baseline scan of a preview | `.github/workflows/zap.yml` | You run it by hand with the preview address |

CI cannot be run from this machine. The first run on GitHub is the first real test of `ci.yml`, so read its result before trusting it.

## Do these on GitHub

1. **Settings, Code security**: turn on Dependabot alerts, Secret scanning, Push protection and Private vulnerability reporting.
2. **Settings, Branches**: protect `main`. Require a pull request, and require the checks `make check and the browser tests`, `static security checks, secrets and the software bill of materials` and `known vulnerabilities (OSV)` to pass.
3. **Settings, Actions, General**: allow only actions pinned by commit, and set the default workflow token to read-only.
4. **Your account**: two-factor authentication with a hardware key or authenticator app.
5. Install the **Renovate** GitHub app on the repository. `renovate.json` is already there. It opens update pull requests only after a version is 14 days old.

## Deploying and the headers

The site is static, so Cloudflare Pages serves `_headers` and `_redirects` from the build. Cloudflare's own Git build cannot make this site: `make brand` and `make media-encode` need `rsvg-convert` and `ffmpeg`. So GitHub Actions builds the site (`.github/workflows/deploy.yml`) and uploads the finished `apps/web/dist` with `wrangler pages deploy`. Cloudflare builds nothing.

Do this once:

1. In Cloudflare, **Workers and Pages**, **Create**, **Pages**, **Upload assets**. Name the project `iitjeekota` (the name in `deploy.yml`). Upload any small file to create it.
2. Create an API token with only **Cloudflare Pages: Edit** on this account (My Profile, API Tokens). Copy the token and your Account ID.
3. In GitHub, **Settings, Environments**: create `preview` and `production`. In `production`, add yourself as a required reviewer, so no deploy goes live without your approval. In both, add the secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
4. Pull requests from this repository then get a noindex preview address. A merge to `main` waits for your approval before it publishes.

After the first deployment, check the headers on the live address:

```
curl -sI https://iitjeekota.com/en/ | grep -i -E "content-security|strict-transport|referrer|x-frame|permissions|cross-origin|x-content-type"
curl -sI https://iitjeekota.com/ | head -3                      # 301 to /en/
curl -s  https://iitjeekota.com/.well-known/security.txt
curl -sI https://iitjeekota.pages.dev/en/ | grep -i x-robots     # noindex
```

Then run the ZAP workflow with a preview address (Actions, ZAP baseline, Run workflow).

## HSTS at launch

HSTS stays off until launch, as `docs/setup/cloudflare.md` says, because it is hard to undo. At launch raise it in stages in `packages/site/security.json` (`hsts`), run `make web-data`, deploy, and wait the full time of each stage while checking the site:

| Stage | `maxAge` | `preload` |
|---|---|---|
| 1 | 300 | false |
| 2 | 604800 | false |
| 3 | 2592000 | false |
| 4 | 63072000 | true, then submit the domain at hstspreload.org |

Preload needs `includeSubDomains` and `www` served over HTTPS as well.

## Open

- The API origin goes into `apiOrigin` in `security.json` when the enquiry service exists, and the policy then lets the page talk to it and nothing else.
- The security contact is the general enquiry email. Change `contactFacts` in `security.json` if you want a separate address.
- Phase 8 adds what only an API needs: origin check, Turnstile, rate limits, webhook signatures and the rest of plan D5.
