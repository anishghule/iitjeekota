# iitjeekota.com build. Every target runs the dsapkit package (tools/dsapkit). `make help` lists them.
PY ?= python3
KIT := PYTHONPATH=tools/dsapkit/src $(PY) -m dsapkit

.PHONY: help fonts fonts-verify metrics media-fetch tokens icons logo favicons og media guide brand site content copy-lint test js-install js-test e2e stills preview map-fetch map web-data web web-dev web-lint check clean

help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | expand -t 16

fonts: ## download the vendored woff2 files and write fonts.lock.json (network)
	$(KIT) fonts
fonts-verify: ## check vendored fonts against fonts.lock.json
	$(KIT) fonts-verify
metrics: ## measure fonts and write fallback and size-adjust metrics (macOS, network)
	$(KIT) metrics
media-fetch: ## fetch supplied media from their recorded sources and write media.lock.json
	$(KIT) media-fetch
tokens: ## build packages/tokens/dist and check contrast
	$(KIT) tokens
icons: ## check icon sources and build the sprite
	$(KIT) icons
logo: ## logo sizes from the official medal
	$(KIT) logo
favicons: ## favicons, app icons and the web manifest
	$(KIT) favicons
og: ## default Open Graph images
	$(KIT) og
media: ## check every media slot and list placeholders and drafts
	$(KIT) media
guide: ## write the brand guide into docs/brand/guide
	$(KIT) guide
brand: ## tokens, icons, logo, favicons, OG images, media check and the brand guide
	$(KIT) brand
site: ## check routes, keywords, links and structured data; write the SEO reports
	$(KIT) site
map-fetch: ## download the area map's OpenStreetMap data and pin it in packages/map/map.lock.json (network)
	$(KIT) map-fetch
map: ## build the area map from the pinned data into packages/map/dist
	$(KIT) map
content: ## check page copy against its template, facts and pages; write docs/content/status.md
	$(KIT) content
copy-lint: ## apply the voice rules to docs and content
	$(KIT) copy-lint
test: ## unit tests
	PYTHONPATH=tools/dsapkit/src $(PY) -m unittest discover -s tools/dsapkit/tests
js-install: ## install the browser packages exactly as locked (pnpm supplies the pinned Node.js)
	pnpm install --frozen-lockfile
js-test: tokens web-data ## type check and unit tests for the browser packages and apps/web
	pnpm exec tsc -p tsconfig.json
	pnpm exec vitest run
web-data: ## write the resolved data and static files apps/web renders (after make brand and make map)
	$(KIT) web-data
web: web-data ## build the site into apps/web/dist and check it (no inline scripts or styles, contract rules)
	pnpm --filter @dsap/web build
	$(KIT) web-lint
web-dev: web-data ## run the site at http://localhost:5179 while editing
	pnpm --filter @dsap/web dev
web-lint: ## check apps/web source against the contract's hard rules, and its last build
	$(KIT) web-lint
e2e: tokens web ## browser checks: scenes on both tiers, autoscroll, the home page (needs: pnpm exec playwright install chromium)
	pnpm exec playwright test
stills: tokens ## render each scene's still-tier image into packages/scenes/dist/stills (reduced motion, Save-Data, no WebGL)
	STILLS=1 pnpm exec playwright test packages/scenes/e2e/stills.spec.ts
preview: tokens ## serve the scene preview at http://localhost:5178
	pnpm preview
check: test js-test fonts-verify media site map content copy-lint web ## everything CI runs
clean: ## remove generated output (sources and locks stay)
	rm -rf packages/tokens/dist packages/icons/dist packages/brand/dist packages/site/dist docs/brand/guide
