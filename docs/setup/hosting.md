# Hosting the enquiry API

The website itself is static and served by Cloudflare, so there is no web server to attack. Only the enquiry service (FastAPI, Phase 8) needs a server. Buy it when Phase 6 starts.

## Recommendation: one small server in India, reachable only through Cloudflare

| Item | Choice | Why |
|---|---|---|
| Server | A Linux VPS in Mumbai or Bangalore: AWS Lightsail (Mumbai) or DigitalOcean (Bangalore). 2 GB memory, 1 to 2 vCPUs, about 50 GB SSD, Ubuntu 24.04 LTS. | Enough for enquiries and the CRM sync. Indian region keeps personal data close and latency low. |
| Backups | The provider's automatic weekly snapshots, plus nightly encrypted database backups to Cloudflare R2 | Two independent copies; R2's free tier covers this size. |
| Connection | Cloudflare Tunnel | The server opens an outbound connection to Cloudflare and accepts no inbound traffic at all, so its address cannot be attacked directly. |
| Firewall | The provider's firewall set to block every inbound port | Nothing reaches the server except through the tunnel. |

Check current prices at checkout; at this size these servers are usually around $10 to $15 a month plus backups.

## Why not a serverless platform

Google Cloud Run and similar services give each app a public address that bypasses Cloudflare. Closing it needs a paid load balancer and Google's firewall, and they bill for every request during an attack. A small server behind a tunnel is simpler, cheaper and has nothing exposed.

## What to do when buying

1. Create the server with **SSH key login only** (no password). Add your public key during setup.
2. In the provider's firewall, allow **no** inbound traffic except SSH from your own IP address. SSH moves behind Cloudflare later as well.
3. Turn on the provider's automatic snapshots.
4. Send Claude only the server's region and size. Access details stay with you; Phase 6 gives the exact setup commands for you to run (Docker, the tunnel, the database, automatic security updates).

## Total security spend

| Item | Cost |
|---|---|
| Cloudflare Pro (DDoS, firewall rules, bots) | about $20 a month billed yearly |
| Turnstile (form bot check) | free |
| VPS with snapshots | about $12 to $18 a month |
| Cloudflare R2 backups | free at this size |
| Domain | already owned |
