Covers: user-visible changes per release and the rules versions in force (spec 9, 16).
Last verified against the code: 2026-10-22.

# Changelog

## 1.1.1 — 2026-10-22

Weekly cadence (spec rev 39, spec 4.1).

- One snapshot every Monday instead of every second Monday: `min_snapshot_age_days` 13 → 6. The job's cron is unchanged (Mondays 05:17 UTC); a forced run on another weekday makes the job skip a Monday that falls within 6 days of it.
- The dashboard warns when the newest snapshot is older than 9 days instead of 16 (`stale_after_days`); its texts say weekly.
- Rules versions unchanged: promo:v1/plans:v1/scoring:v1.

## 1.1.0 — 2026-10-13

Public trends edition (spec rev 38, spec 16, ADR-0009). Implemented; the site goes live after the go-public steps of spec 16.5 (`docs/BACKLOG.md`).

### Data and privacy

- VINs, dealer stock numbers (`komisja`), offer links, `kod_audi` and dealer phone numbers are dropped right after schema validation and never written anywhere, not even as hashes. Unknown fields that look like an identifier or a URL are dropped too (spec 3.5).
- Slider responses are kept only as item counts per model. Offers carry badge bits only (spec 3.4, 5.2).
- The site’s bundle is no longer downloaded or archived; only its hash is recorded. A run makes exactly 10 requests (spec 3.1, 4.2).
- An offer exists only inside its snapshot, as `offer_id` = `<date>/<n>` in a canonical order. A single car is no longer followed across runs: per-car history, days listed, sold or withdrawn cars and dealer moves are gone (spec 5.5).
- The User-Agent names the public repository instead of a contact e-mail (spec 4.2).
- The release 1.0 raw file of 13 Oct 2026 was redacted and kept as snapshot zero in the private repository (spec 16.4).

### Publication

- Two repositories: the public `rlgdev/audilitics` holds code, rules, docs and aggregate data and serves the Pages site; the private `rlgdev/audilitics-private` runs the scheduled collector and holds the redacted offers, exports and run reports (spec 9, 10).
- The public site shows aggregates only. Every public figure rests on at least 3 offers of that snapshot, and every price, rate, discount or score figure on at least 3 priced offers (spec 5.5).
- A publication guard checks every public tree for identifiers, links to audi.pl, dealers, files outside the public layout and figures below the minimum group size. It runs before every push, in CI and before every Pages deploy; a failure fails the run and opens a `publication-guard` issue (spec 10.5).
- An identifier check runs over all of the private repository’s `data/` in every run (spec 10.5).

### Analytics

- Configurations (model + engine + model code + model year) are the unit compared across runs and the unit of publication (spec 5.1).
- Changes compare configurations and models: new and gone configurations with a reason, price drops and rises of the median special price, stock by model with net added and removed, promo changes (spec 6.2).
- The like-for-like index is built from configurations with at least 3 priced offers in two consecutive runs (spec 6.1).
- Deal score momentum uses the fall of the configuration’s median price. Best deals rank configurations by best and median score, with the median score components (spec 6.3).
- Hot deals of the last month are configurations (spec 6.5).
- Trends add the site’s own slider counts per model, segment and total, and net stock movement (spec 6.1).

### Dashboard

- One app, two builds. The public build has Overview, Model, Best deals, Changes and About. The private build, run only on the owner’s machine, adds Offers, Dealers and the Car page and the Dealer filter (spec 7).
- Public tables are configuration tables with a configuration drawer; the offer table moved to the private build (spec 7.3).
- The Changes page has a run picker: each run is compared with the run before it (spec 7.1).
- No page links to audi.pl; About names the source as plain text and states that the figures are aggregates, not offers within the meaning of the Civil Code, and that the project is not affiliated with Audi or Volkswagen Group Polska (spec 7.5).

### Rules versions

Unchanged from 1.0.

| File | Version | valid_from |
|---|---|---|
| `rules/promo_rules.yaml` | promo v1 (bundle `main.20ab651335fb4daeebc8.js`) | 2026-10-13 |
| `rules/plans.yaml` | plans v1 | 2026-10-13 |
| `rules/scoring.yaml` | scoring v1 | 2026-10-13 |

### Snapshot zero

2026-10-13, status `ok`, redacted: 4,768 offers, 53 models, 38 dealers, 3,092 versions, 191 configurations of which 149 are published (`docs/data-source.md`).

### Known deviations from the specification

- The identifier check over the private tree does not treat `offer_id` as an identifier; over the public tree it does (ADR-0006, Release 1.1 (a)).
- `new_config` is not set on the first `ok` run ever (ADR-0006, Release 1.1 (b)).
- The Business Edition slider-versus-badge gate compares the slider with the `business_edition` flag (ADR-0006, Release 1.1 (c)).
- The migrated raw file keeps the bundle name and hash (ADR-0006, Release 1.1 (d)).
- The promo mix chart still uses grouped bars, not stacked bars (ADR-0007; ADR-0006, Release 1.1 (e)).

## 1.0.0 — 2026-10-13

First release (spec 2, release 1).

### Data

- Collector reads the full "gotowe do odbioru" stock from the site's JSON feed every 14 days: every car, prices, 30-day reference prices, Audi Perfect Lease rate, dealer, all five promo sliders, the `pks` service-package flag and all offer-card badges (spec 3, spec 4).
- At most 10 budgeted requests per run, 1 s apart, identified User-Agent, immediate stop on HTTP 403 or 429 (ADR-0005).
- Every raw response and every snapshot is archived; any run can be replayed and all history rebuilt (spec 4.4, ADR-0008).
- Models, engine groups and dealers are discovered from the feed; models with no cars for three runs retire on their own and come back when cars return (spec 4.6).
- Quality gates mark a snapshot `suspect` below 80 % of the previous count and open GitHub issues for failures, blocks, schema changes and bundle changes (spec 4.3).
- Per-run Excel workbook (`data/exports/<date>.xlsx`) and `latest.csv`; Markdown run report per run.

### Analytics

- Per-model, per-segment and per-engine trends: count, min / median / max special price, median discount %, rates per plan, promo counts, like-for-like price index (spec 6.1).
- Changes between consecutive snapshots: new, gone, price drops and rises, rate, promo and dealer changes, new, retired and returned models (spec 6.2).
- Deal score 0-100 with a five-part breakdown, flags (`lowest_ever`, `biggest_drop_this_run`, `last_one`, `long_listed`) and rankings (spec 6.3).
- Hot deals of the last month (spec 6.5); they appear from the second snapshot on.
- Payment-plan assumptions `APL-1`, `APL-2`, `APL-2-EV`, `APL-3` next to every rate (spec 6.4).

### Dashboard

- Seven pages: Overview (KPIs, hot deals, trend charts, model board), Model, Best deals, Changes, Dealers, Car, About (spec 7.1).
- One filter row (period, segment, model, engine group, dealer, promo, plan) stored in the URL, so every view is a shareable link (spec 7.2).
- Car table with column chooser, sorting, virtualised rows and CSV export of the current view (spec 7.3).
- Light, dark and system themes; every chart has a table view (spec 8).

### Rules versions

| File | Version | valid_from |
|---|---|---|
| `rules/promo_rules.yaml` | promo v1 (bundle `main.20ab651335fb4daeebc8.js`) | 2026-10-13 |
| `rules/plans.yaml` | plans v1 | 2026-10-13 |
| `rules/scoring.yaml` | scoring v1 | 2026-10-13 |

### First live snapshot

2026-10-13, status `ok`: 4,768 cars, 53 models, 38 dealers, 3,092 versions (`docs/data-source.md`).

### Known deviations from the specification

- Business Edition badge count is 2,847, not 2,617 (ADR-0006).
- `lowest_ever` is per configuration, not per `version_key` (ADR-0006).
- The promo mix chart uses grouped bars, not stacked bars (ADR-0007).
- The `get-filtered.php` cross-check is not called (ADR-0005).
