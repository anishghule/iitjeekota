# Cloudflare: account, domain and protection

Cloudflare sits in front of everything: it serves the site, absorbs DDoS attacks, filters bad traffic and checks that enquiries come from people. You carry out these steps; nobody needs to share a login with Claude.

Today iitjeekota.com redirects to `https://www.dsapghuletutorials.com/courses/jee` through the registrar's forwarding. Step 5 keeps that working on Cloudflare until the new site launches.

## What to buy

| Item | Plan | Why |
|---|---|---|
| Cloudflare for iitjeekota.com | **Pro**, billed yearly (third-party listings show about $20 a month yearly, $25 monthly; check at checkout) | Adds the Cloudflare Managed and OWASP rule sets (Free has only a basic set), 2 rate limiting rules with windows up to one minute (Free: 1 rule, 10 seconds) and stronger bot controls. DDoS protection is included on every plan. |
| Turnstile (bot check on the enquiry form) | Free | Unlimited checks, up to 20 widgets. No need to buy hCaptcha. |
| Business plan | Not now | Only if the enquiry form is attacked for weeks: 5 rate limiting rules with windows up to 10 minutes. |

Sources: Cloudflare's [managed rules](https://developers.cloudflare.com/waf/managed-rules/), [rate limiting](https://developers.cloudflare.com/waf/rate-limiting-rules/) and [Turnstile plans](https://developers.cloudflare.com/turnstile/plans/) pages, checked 2026-10-30.

## 1. Create the account

1. Go to [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up).
2. Use an email D-SAP owns for the long term (a shared mailbox such as web@ on D-SAP's own domain), not a personal address.
3. Verify the email.

## 2. Lock the account

1. Click the person icon (top right), then **My Profile**, then **Authentication**.
2. Turn on **Two-Factor Authentication**. A hardware security key is the strongest choice; an authenticator app is fine. Store the backup codes somewhere safe and offline.

## 3. Add the domain and choose Pro

1. On the account home, choose **Add a domain** (it may say **Onboard a domain**).
2. Enter `iitjeekota.com`, keep **Quick scan for DNS records**, continue.
3. Choose the **Pro** plan and pay.

## 4. Review the DNS records Cloudflare found

1. Records pointing at `207.207.210.50` or `207.207.210.23` belong to the registrar's forwarding service. Delete them.
2. Keep any **MX** or **TXT** records if anyone receives email at @iitjeekota.com. If nobody does, delete those too and do step 10.
3. Add two placeholder records so Cloudflare can answer for the domain until the site launches:
   - Type **AAAA**, Name `@`, IPv6 address `100::`, Proxy status **Proxied** (orange cloud).
   - Type **AAAA**, Name `www`, IPv6 address `100::`, Proxy status **Proxied**.

## 5. Keep today's redirect until launch

1. Go to **Rules**, then **Redirect Rules**, then **Create rule**.
2. Name: `Until launch: D-SAP JEE page`.
3. **If incoming requests match**: All incoming requests.
4. **Then**: Type **Static**, URL `https://www.dsapghuletutorials.com/courses/jee`, Status code **302**, **Preserve query string** on.
5. **Deploy**. This rule is removed on launch day.

## 6. Switch the nameservers at the registrar

1. Cloudflare now shows two nameservers ending in `ns.cloudflare.com`. Copy both.
2. Log in where iitjeekota.com was bought.
3. Turn **off** the domain forwarding there, and turn **off** DNSSEC there if it is on (it is turned back on through Cloudflare in step 8).
4. Open the domain's **Nameservers** setting, choose custom nameservers, replace the existing ones with Cloudflare's two, save.
5. Back in Cloudflare, wait until the domain shows **Active** (minutes, sometimes up to a day). Then open `http://iitjeekota.com`: it must still land on the D-SAP JEE page.

## 7. Encryption

In **SSL/TLS**:

1. **Overview**: encryption mode **Full (strict)**.
2. **Edge Certificates**: **Always Use HTTPS** on, **Minimum TLS Version** 1.2, **TLS 1.3** on, **Automatic HTTPS Rewrites** on.
3. Leave **HSTS** off for now. It is switched on at launch (Phase 10), because it is hard to undo.

## 8. DNSSEC

1. **DNS**, then **Settings**, then **Enable DNSSEC**.
2. Cloudflare shows a DS record. Add it at the registrar (the DNSSEC section of the domain). Cloudflare confirms when it is working.

## 9. Firewall and bots

In **Security**:

1. **WAF**, **Managed rules**: deploy the **Cloudflare Managed Ruleset** and the **Cloudflare OWASP Core Ruleset** with their default settings.
2. **Bots**: turn on bot protection with **Definitely automated** set to **Block**. Keep **Verified bots** allowed, so Google and Bing can still read the site.
3. **Settings**: **Security level** Medium, **Browser Integrity Check** on.
4. Rate limiting is added in Phase 8 when the enquiry form exists. Claude will give the exact rule (path, requests per minute, block time).
5. In an emergency, **Overview**, then **Under Attack Mode**, adds a check for every visitor. Turn it off when the attack ends.

## 10. Stop others sending email as iitjeekota.com

Only if nobody sends or receives email at @iitjeekota.com. In **DNS**, add:

| Type | Name | Content |
|---|---|---|
| TXT | `@` | `v=spf1 -all` |
| TXT | `_dmarc` | `v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s` |
| MX | `@` | `.` with priority `0` |

If D-SAP will use email on this domain, skip this and tell Claude which mail service it will use.

## 11. Turnstile keys for the enquiry form

1. In the sidebar, **Turnstile**, then **Add widget**.
2. Name `iitjeekota enquiry form`, hostnames `iitjeekota.com` and `www.iitjeekota.com`, widget mode **Managed**.
3. Copy the **site key** and **secret key** into `.env.local` at the project root (never committed) as `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY`.

## 12. A second administrator

**Manage Account**, then **Members**, invite one more trusted D-SAP person as Administrator, so the account never depends on one login.

## Later (Phase 6)

Deployment will connect Cloudflare to the GitHub repository, so a merge to `main` that you make publishes the site and other branches publish noindex previews. Claude will give the exact steps when the site build exists. No Cloudflare API token is needed for that.
