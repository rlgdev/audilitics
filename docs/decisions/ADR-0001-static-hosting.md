# ADR-0001: Static hosting on GitHub Pages

Status: Accepted, 2026-10-13.

Context: The dashboard needs a home with no server to run, patch or pay for, and the data changes only every 14 days (spec 1, spec 2).

Decision: Publish a static single-page app (Vite, React, TypeScript, hash routing) on GitHub Pages from the same repository. The collector runs in GitHub Actions and commits prepared JSON to `data/`; `deploy-pages.yml` copies the browser-facing files into the site (spec 10).

Consequences: All computation happens in the collector; the browser only filters and renders. There is no database and no API. Deep links work through hash routes without a 404 fallback. Access control is whatever GitHub Pages offers (spec 10.4). The repository grows by about 20 MB a year (spec 5.4).
