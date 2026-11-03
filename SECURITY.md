# Security

## Reporting a problem

If you find a security problem in iitjeekota.com or its code, please email ghulesir@dsapghuletutorials.com with the details. The same address is listed in `https://iitjeekota.com/.well-known/security.txt`.

Please include the page or file, what you did and what happened. Do not access other people's data, and do not test with denial-of-service traffic. We will reply, fix the problem, and tell you when it is fixed.

If the repository's host offers private vulnerability reporting, you may use that instead.

## What is in scope

- The website at iitjeekota.com and its previews.
- The enquiry service, once it exists (Phase 8).
- This repository: build tools, workflows and configuration.

## How the project protects itself

The rules are in `CLAUDE.md` section 5 and the setup steps in `docs/setup/security.md`. In short: no third-party scripts, styles, fonts or embeds, a strict Content Security Policy tested in a real browser, hidden data removed from every image and video, exact dependency versions that are at least 14 days old, and scans for secrets, known vulnerabilities and code flaws on every change.
