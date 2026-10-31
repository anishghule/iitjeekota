# The site header and menu

Built (2026-10-31) as `apps/web/src/components/blocks/SiteHeader.astro`, with the menu behaviour in `apps/web/src/islands/nav.ts`. It is the same on every page and in all three languages. The items come from `packages/site/routes.json`: pages with a `nav` number, in that order.

## Wide screens: a header that melts into the page

- The header is fixed at the top. The page scrolls underneath it.
- **No bottom border, ever.** v3.2 switched to a solid bar with a 1 px line once the page scrolled. This header never does.
- **Two layers fade out together towards the bottom edge:**
  - **The tint:** the page background colour, strong at the top and transparent at the bottom edge. It is made with `color-mix()` on the surface role `--bg`, so it follows the ink and chalk surfaces.
  - **The blur:** a `backdrop-filter: blur()` on a layer behind the links, masked with a top-to-bottom `mask-image` gradient. The blur is strongest at the top and fades to none at the bottom edge.

  Because the tint and the blur both fade, text scrolling up under the header softens and dims gradually, with no line where the header starts.
- The links sit in the solid top part, so they keep full contrast. The contrast pair is checked against the tint at its strongest.
- The tint, blur strength, fade start, the faded layer's height and the bar height are the `nav` tokens in `packages/tokens/tokens.json`, not values in the component.
- Long page names get a short link text in `packages/site/routes.json` (`navNames`), for example "Pimpri-Chinchwad". Breadcrumbs and titles keep the full name.
- Where `backdrop-filter` is not supported, the tint alone does the job. Its top is opaque enough to read the links over any content.

## Phones and narrow screens: a hamburger menu

- Below the navigation breakpoint (`nav.menu-from`, now `xl`: five links and the language switch need that width), the links fold into a hamburger button. The brand mark and the call button stay visible in the bar.
- **The button** is a three-line icon from the icon set. When open, it turns into a cross: the top and bottom lines rotate, the middle fades, using the `motion` tokens. It carries `aria-expanded` and `aria-controls`, and its label says what it does ("Menu", "Close menu").
- **The menu** is a full-screen sheet on the page surface. It is a dialog with `aria-modal`. It lists:
  - the same links, large and easy to tap
  - the language switch (English, हिंदी, मराठी)
  - call and WhatsApp
- **While it is open:**
  - focus stays inside the menu
  - Esc or the cross closes it, and focus returns to the button
  - the page behind does not scroll
  - autoscroll holds still (`@dsap/motion` already pauses for an open `aria-modal` dialog)
- Under reduced motion, it opens and closes without animation.

## Carried over from v3.2

- The underline that grows under a link on hover, and stays under the current page's link.
- The menu built from the same list as the desktop links, so the two can never differ.
- Brand-name text dropped on the narrowest screens, keeping the medal mark.
