# Audilitics

Audilitics is a public dashboard of price trends in the Audi “gotowe do odbioru” stock (new cars ready for pickup)
listed on gotowedoodbioru.audi.pl. A collector reads the site’s JSON feed every 14 days. The public site shows
aggregates only: trends per model, segment and engine group, model statistics, and deal scores per configuration
(model + engine + model code + model year). Offer-level tables stay in a private repository and are viewed locally.

Live dashboard: https://rlgdev.github.io/audilitics/ (online once the go-public steps of
[spec 16.5](docs/SPEC.md#165-going-public) are done).

## Notice

The figures are aggregates of offers published on gotowedoodbioru.audi.pl on the stated dates. They are not offers
within the meaning of the Civil Code. The project is not affiliated with Audi or Volkswagen Group Polska.

No VIN, dealer stock number, offer link or dealer phone number is collected (spec 3.5). Nothing on the site or in
this repository links to audi.pl or to an individual offer; the source is named as plain text. No Audi brand assets
are reproduced. Every public figure rests on at least 3 offers (spec 5.5).

## Start here

| I want to… | Go to |
|---|---|
| See the live dashboard | https://rlgdev.github.io/audilitics/ |
| Run the collector locally | `make setup`, then `make collect FIXTURE=1` (synthetic fixture, no network, writes `build/fixture-data/`). With the private repository cloned next to this one: `make collect FIXTURE=real DATA=../audilitics-private/data`. Live runs belong to the private repository’s job ([runbook](docs/runbook.md#forcing-a-run)) |
| Run the private dashboard | Clone `rlgdev/audilitics-private` next to this repository, then `make web EDITION=private DATA=../audilitics-private/data`. Local only, never deployed (spec 7) |
| Add a promo rule | [rules/promo_rules.yaml](rules/promo_rules.yaml): add a new rule set with `valid_from`, never edit an old one ([runbook](docs/runbook.md#re-verifying-rules-after-a-bundle-change)) |
| Fix a failed run or a guard failure | [docs/runbook.md](docs/runbook.md): [failed run](docs/runbook.md#failed-run-collector-failure), [guard failure](docs/runbook.md#guard-failure-publication-guard) |
| Change the score | [rules/scoring.yaml](rules/scoring.yaml) (new rule set), then `make rebuild DATA=../audilitics-private/data` ([analytics](docs/analytics.md#deal-score-spec-63)) |
| Add a page | `web/src/pages/` (public) or `web/src/pages/private/` (private build only), route in [web/src/app/routes.tsx](web/src/app/routes.tsx), rules in [docs/design-system.md](docs/design-system.md) |
| Understand what the project must do | [docs/SPEC.md](docs/SPEC.md) (rev 38) |
| Understand the feed and its fields | [docs/data-source.md](docs/data-source.md) |
| Understand the files under `data/` | [docs/data-model.md](docs/data-model.md) and [collector/schemas/](collector/schemas/) |
| Know why something is built the way it is | [docs/decisions/](docs/decisions/) |
| See open owner decisions | [docs/BACKLOG.md](docs/BACKLOG.md) |

## The three commands that matter

```bash
make setup               # .venv with the collector (dev extras), npm ci in web/
make collect FIXTURE=1   # three synthetic runs, no network, into build/fixture-data/
make test                # ruff, mypy, pytest, tsc, eslint, vitest, palette validator, guard on data/
```

None of them needs the private repository (spec 12.1). To look at the synthetic data in the dashboard, run
`make web EDITION=private DATA=build/fixture-data` after `make collect FIXTURE=1`.

Other targets:

| Command | What it does |
|---|---|
| `make collect DATA=<dir>` | Live run against the site into a private data directory (10 requests, 1 s apart). Normally only the private repository’s job does this |
| `make collect FROM=<file> DATA=<dir>` | Replay one redacted raw file, for example `<dir>/raw/2026-10-27.json.gz` |
| `make collect FIXTURE=real DATA=../audilitics-private/data` | Run on the redacted 13 Oct 2026 fixture of the private repository |
| `make rebuild DATA=<dir>` | Replay every raw file of `<dir>` in date order, after a rules or scoring change |
| `make guard` | Publication guard on `data/` of this repository; `GUARD_DIR=<dir>` checks another public tree |
| `make e2e` | Playwright smoke tests and screenshots of both builds on synthetic data |
| `make web` | Vite dev server of the public build with the local `data/` |
| `make web EDITION=private DATA=../audilitics-private/data` | Vite dev server of the private build on a private checkout |

The Makefile runs on Linux, macOS and Git Bash on Windows. Every target is a thin wrapper around
`PYTHONPATH=collector python -m collector --data-dir <dir> collect|rebuild`, `python -m collector guard <dir>`,
`python -m collector idcheck <dir> [--public]` or `npm run <script>` in `web/`.

## How it fits together

```text
gotowedoodbioru.audi.pl JSON feed
  -> collector: job collect.yml in rlgdev/audilitics-private, every second Monday,
     code and rules/*.yaml from rlgdev/audilitics; identifying fields dropped at ingestion
  -> data/ of the private repository: redacted raw feed, snapshots, offer-level files, exports, run reports
  -> data/public/ mirrored onto data/ of rlgdev/audilitics (fine-grained token)
  -> deploy-pages.yml -> GitHub Pages (public build, aggregates only)
```

Two repositories (spec 9, 10):

| | Public `rlgdev/audilitics` (this one) | Private `rlgdev/audilitics-private` |
|---|---|---|
| Holds | Code, rules, docs, aggregate `data/` | `data/` (redacted raw feed, snapshots, `private/`, `public/`, exports, reports), `fixtures/2026-10-13/` |
| Workflows | `deploy-pages.yml`, `ci.yml` | `collect.yml`, `ci.yml` |
| Writes `data/` | Never by hand: `data/` only receives pushes from the private job | `collect.yml` every 14 days |
| Secrets and variables | None | Secret `PUBLIC_REPO_TOKEN` (fine-grained, Contents read and write on `rlgdev/audilitics` only); variable `COLLECTOR_REF` (default `main`) |
| Dashboard | Public build on GitHub Pages | Private build, on the owner’s machine only |

Locally the two clones sit side by side, because the Makefile expects the private checkout at `../audilitics-private`:

```text
<folder>/
  audilitics/           this repository
  audilitics-private/   the private repository
```

| Area | What lives there |
|---|---|
| `collector/` | Python 3.12 package: fetch, redact, normalise, rules, analytics, diff, public tree, guard, exports, report, issues (spec 4–6, 10.5) |
| `collector/schemas/` | JSON Schema files of the stored shapes ([data model](docs/data-model.md#json-schema-files)) |
| `collector/tests/fixtures/synthetic/` | Three generated runs with invented prices and dealers, used by CI |
| `collector/tools/redact_raw_1_0.py` | One-time migration of a release 1.0 raw file (spec 16.4) |
| `rules/` | Promo, plan, scoring and model-override rules as versioned YAML (spec 4.5) |
| `data/` | The public tree of spec 5.3, written only by the collector job |
| `web/` | The dashboard, one app with a public and a private build (spec 7–8) |
| `docs/` | Spec, data source, data model, analytics, design system, design plan, runbook, ADRs, changelog, backlog |
| `.github/workflows/` | `deploy-pages.yml`, `ci.yml` (spec 10.1) |

## Going public

The public repository and the Pages site go live only through the steps of
[spec 16.5](docs/SPEC.md#165-going-public): a fresh repository with no history from release 1.0, one forced run, the
guard and the public-history check, then visibility and Pages. The procedure and the checks are in
[docs/runbook.md](docs/runbook.md#going-public-spec-165).
