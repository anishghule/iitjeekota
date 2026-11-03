# 0009. Security headers and the supply chain

Date: 2026-11-01. Status: accepted.

## Context

Plan D5 asks for a strict Content Security Policy, the standard response headers, locked and scanned dependencies, and a scan of every preview. Phase 6 left all of it undone: no headers file, no CI, no scanner configuration. The site is static and ships no third-party code, so a very strict policy is possible. Guidance was read on 2026-11-01 from Cloudflare Pages' headers documentation, MDN, hstspreload.org, Renovate's documentation and RFC 9116.

## Decision

1. **One policy, from data.** `packages/site/security.json` holds the Content Security Policy, the other headers and the HSTS stages. `make web-data` writes `_headers` from it. `default-src 'none'` and every fetch directive is `'self'`. There is no inline script, style or event handler, no `eval`, no `data:` or `blob:`, no framing and no `<base>`.
2. **The policy is tested, not assumed.** `make web-lint` finds what it would block in the built pages. A browser test loads nine real pages under the exact headers. It scrolls them so the 3D world, the pinned sections and the film start, and fails on any violation. Another test proves that an injected inline script and a request to another site are blocked.
3. **A weaker policy cannot be committed.** `make site` refuses `unsafe-*`, wildcards, `data:`, plain http, a framing allowance or a missing directive. The API origin is the only source that may be added.
4. **HSTS is staged and off until launch,** as `docs/setup/cloudflare.md` says. Preload needs a year, `includeSubDomains` and `preload`; the build enforces that.
5. **security.txt follows RFC 9116.** Contact is the confirmed email fact. The build fails once Expires has passed or if it is more than a year away.
6. **Pages.dev addresses are noindex** through a `_headers` rule, and the root redirect is a real 301 in `_redirects`.
7. **Supply chain.** Renovate waits 14 days, pins exact versions and pins GitHub Actions by commit. The CI tools are hash-locked. CI runs ruff and bandit, gitleaks, OSV-Scanner, `pnpm audit`, `pip-audit` on its own tools and a CycloneDX bill of materials, with a read-only token and nothing that deploys. The exceptions file `osv-scanner.toml` gives every exception an expiry.
8. **Findings fixed in this change.** Icon files are refused if they declare a document type or entity before parsing. Each reviewed network and subprocess call carries its reason. One high advisory in a development dependency, happy-dom, is held back only by the 14-day rule and is listed in `osv-scanner.toml` until 2026-11-05.

## Semgrep is deferred

Plan D5 names Semgrep. Release 1.181.0 (the newest at least 14 days old) pins `mcp` 1.29.0 and `opentelemetry-api` 1.37, and `pip-audit` reports five known vulnerabilities in them. Its dependency closure is also about 60 packages, including an MCP server stack the project does not use. That fails the rule that the tools themselves audit clean. Semgrep goes back in when a release at least 14 days old pins fixed versions. Until then JavaScript and TypeScript get the browser policy test, `pnpm audit` and OSV-Scanner, but no static code analysis. Say so if you want an ESLint security plugin as the stand-in.

## Not decided here

Where the site is built and deployed (`docs/setup/security.md`). The API's own protections come with Phase 8.

## Consequences

Anything that would weaken the policy fails a build. The headers are only proven once they are live, so the first deployment must repeat the checks in `docs/setup/security.md`.
