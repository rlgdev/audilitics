> Exported from the Claude Doc "Audilitics — Specification" (doc rev 65, 2026-10-13; spec rev 38, public trends edition), with rev 39 (2026-10-22, weekly cadence) applied to this export. Source of truth for scope.

# Audilitics — Specification

2026-10-22 · @Roman · rev 39

Audilitics is a public GitHub Pages dashboard of price trends in the Audi “gotowe do odbioru” stock, fed every week by an automated collector. The public site shows aggregates only: trends, model statistics and deal scores per configuration. Offer-level tables stay in a private repository and are viewed locally. No VIN, dealer stock number, offer link or phone number is collected, and nothing links to individual offers. This document is the hand-off for implementation; no code is included. Release 1.0 is already built; section 16 lists what changes for release 1.1.

## 1. At a glance

Release 1.1, the public trends edition, answers three questions for every Audi model in the “gotowe do odbioru” stock, from aggregates only: what is in stock now, how prices and lease rates moved every week, and which configurations are the best deals today.

```text
audi.pl JSON feed -> collector (private repo, GitHub Actions, every week, rules/*.yaml)
  -> redacted offers in the private repo (data/)         -> private dashboard (local build, never deployed)
  -> aggregates pushed to the public repo (data/)        -> public dashboard (GitHub Pages)
```

The collector is the only moving part: it reads the feed, drops the identifying fields as soon as the response is validated, applies the rules valid on that date, writes offer-level files to the private repository and aggregate files to the public one, and the push to the public repository publishes the site.

| Part | Decision |
|---|---|
| Repositories | Public `rlgdev/audilitics`: code, rules, docs, aggregate data and the GitHub Pages site. Private `rlgdev/audilitics-private`: the scheduled collector job, redacted offers, exports, run reports |
| Collector | Python 3.12 package (code in the public repository) run every week by a scheduled GitHub Actions job in the private repository; reads the site’s own JSON feed, no browser automation |
| Data minimisation | `vin`, `komisja`, `link`, `kod_audi` and `telefon` are dropped right after schema validation and never written anywhere, not even as hashes (3.5); a single car is never followed across runs |
| Unit of publication | The configuration: model + engine + model code + model year. Every public figure rests on at least 3 priced offers (minimum group size, 5.5) |
| Storage | Git itself: plain JSON for what the dashboards read, gzipped JSON for archives; no database, no server |
| Public dashboard | Static single-page app (Vite + React + TypeScript) built with `EDITION=public`, deployed to GitHub Pages from the public repository, hash routing (`#/model/q5`) |
| Private dashboard | The same app built with `EDITION=private`, run on the owner’s machine against a checkout of the private repository; never deployed |
| Charts | Apache ECharts 5 with one project theme built from the tokens in section 8 |
| Tables | TanStack Table + TanStack Virtual: configuration tables in both builds, ~5,000-row offer tables in the private build |
| Analytics | Computed by the collector at run time and stored as JSON; the browser only filters and renders |
| Coverage | Every offer in the feed (4,768 on 13 Oct 2026) and every card badge, aggregated; every redacted snapshot kept in the private repository |
| Rules | Promo, plan and scoring rules live in versioned YAML (`rules/`) with a `valid_from` date, never in code |
| Models | Discovered from the feed on every run: a model that appears is added, a model with no offers for three consecutive runs is retired; nothing is hard-coded (4.6) |
| Publication guard | A check run before every push and in the public repository’s CI; it fails when public data holds an identifier, a link to audi.pl, a dealer, a file outside the public layout, or a figure resting on fewer than 3 offers (10.5) |

Sections 2–6 define the data side, 7–8 the dashboards, 9–12 delivery, 13–15 the hand-over material, 16 the change from release 1.0.

## 2. Scope

Release 1.1 covers the full new-car stock on gotowedoodbioru.audi.pl, collected every week and published as trends, model statistics and configuration-level deal scores; offer-level data stays private; nothing requires a server.

In scope (release 1.1)

- Collect every offer in the feed on each run, without identifiers: model, engine, model code, years, prices, 30-day reference prices, Audi Perfect Lease rate, dealer number and name, offer-card badges; per-model counts of the five promo sliders and of the service-package filter.
- Keep every redacted snapshot in the private repository; discover new models, engine groups and dealers from the feed and retire models that leave the stock.
- Public: trends per model, segment and engine group (count, min / median / max special price, discount %, rate, promo mix, net stock movement, like-for-like price index); configuration tables; configuration-level deal scores and rankings; hot deals of the last month (by configuration) on the main screen; changes between consecutive runs at configuration and model level.
- Private, viewed locally: offer tables with the per-offer deal score, the Car page (one offer on one date), dealer statistics, the Excel workbook and CSV of each run.
- Public dashboard pages: Overview, Model, Best deals, Changes, About. The private build adds Offers, Dealers and Car (section 7).
- Exports: CSV of any table view in the browser (aggregates in the public build, offers in the private build); an Excel workbook per run in the private repository.
- Run report and automatic GitHub issue in the private repository when a run fails, is blocked or fails the publication guard.

Out of scope (release 1.1)

- VINs, dealer stock numbers (`komisja`), offer links and any other link to an individual offer, dealer phone numbers: not collected, not derived, not stored (3.5).
- Following a single car across runs: per-car price history, days listed, sold or withdrawn cars, dealer moves.
- Publishing any offer-level row, any dealer name or dealer statistic, or any link to audi.pl.
- Car photos, Audi logos, fonts and other brand assets; copies of the site’s JavaScript bundle.
- Contact forms, lead handling, anything that writes to the Audi site.
- Used cars, other brands, other markets.
- Notifications (Slack or Teams digest) — release 2.
- History before the first collector run. The live run of 13 Oct 2026 stays as snapshot zero after redaction (16.4).
- User accounts and a hosted private dashboard.

| Constraint | Consequence for the design |
|---|---|
| Static hosting only (GitHub Pages) | All computation happens in the Action; the browser reads prepared JSON |
| Unofficial data source; §8.2–8.3 of the audi.pl Regulamin restrict reproducing and publishing the site’s information | Only aggregates are published; identifiers and links are never collected; rules are versioned; the bundle hash is watched for changes (11, Legal) |
| One run per week | Trends are weekly points; the Changes view compares consecutive runs |
| Request budget | At most 10 HTTP requests per run, identified User-Agent, no image or bundle downloads |
| Reproducibility | A run can be replayed from the redacted `data/raw/<date>.json.gz` in the private repository to rebuild every derived file, public and private |
| Site content is Polish | Promo names, engine strings and footnotes are stored verbatim; UI labels are English with Polish terms kept where they name a site feature |

## 3. Data source

The site is an Angular app that loads its whole stock from a few unauthenticated JSON endpoints under `https://gotowedoodbioru.audi.pl/ajax/`; one request with a large page size returns every car. Verified 13 Oct 2026 (4,768 cars, 53 models, 38 dealers).

### 3.1 Endpoints

| Endpoint | Returns | Collector use |
|---|---|---|
| `GET /ajax/get2.php?p=1&c=20000&s=price&d=asc` | `{count, items[]}` — every offer, fields in 3.3; ~2.0 MB; `Content-Type: text/html` although the body is JSON | The main pull, once per run; items are redacted right after validation (3.5) |
| `GET /ajax/get2.php?…&<slider params>` | Same shape, filtered | One call per slider (3.4); only the number of items per model is kept |
| `GET /ajax/get-filtered.php?<filters>` | `{model_counts: {model: n}}` | Not called (request budget, ADR-0005) |
| `GET /ajax/data_models2.json` | Per model: `count, engine[], business_edition, moj_elektryk, rp[], stock_cleaning[], perfect_financing` | Model discovery (4.6) and engine groups |
| `GET /ajax/data_dealers2.json` | `{dealer_nr: dealer name}` | Dealer directory, private repository only |
| `GET /ajax/image.php?…` | Car image | Never fetched |
| `GET /main.<hash>.js` (name read from `/`) | App bundle; badge and footnote rules live here | Never downloaded; the hash in the file name is recorded per run and a change raises a rules-review issue |

### 3.2 Query parameters of `get2.php` and `get-filtered.php`

| Parameter | Meaning | Values seen |
|---|---|---|
| `p`, `c` | Page, page size | Site uses `c=12`; `c=20000` returns all |
| `s`, `d` | Sort field and direction | `price`, `asc` or `desc` |
| `m[]` | Model name filter (repeatable) | `Audi Q7` |
| `mc[]` | Model-code prefix filter with wildcard | `4MQ*` |
| `e[]` | Engine group filter | values of `silnik2` |
| `a_nr[]` | Dealer number filter | `0090` |
| `bo` | Slider “Najlepsza oferta z rocznika 2026” | `Tak` |
| `l101badge` | Slider “Leasing 101%” | `Tak` |
| `pu` | Slider “Pakiet ubezpieczeń za 1 zł” | `Tak` |
| `b` | Slider “Oferta Business Edition” | `Tak` |
| `rm` | Model-year filter, used by the Q7 Final Edition slider together with `m[]` and `mc[]` | `2026` |
| `pks`, `l101`, `pf`, `me` | Service package, legacy leasing flag, perfect financing, “Mój elektryk” | Present in the app, no slider today; collect `pks=Tak` anyway |

Sliders combine as AND. The page opens with `bo=Tak` switched on, which hides about half of the stock; the collector always pulls with no filters first.

### 3.3 Field dictionary (one item of `get2.php`)

| Field | Type as sent | Meaning | Observed 13 Oct 2026 |
|---|---|---|---|
| `vin` | string | Vehicle identification number. **Discarded at ingestion (3.5)** | unique per item |
| `model` | string | Model name as shown on the tile | 53 distinct |
| `silnik` | string | Engine line on the card, e.g. `TFSI 110(150) kW(KM) S tronic` | empty for RS 5 (23 cars) |
| `silnik2` | string | Engine group used by the engine filter | 14 values incl. `modele S`, `modele RS`, empty |
| `komisja` | string | Dealer stock (commission) number, part of the offer link. **Discarded at ingestion (3.5)** | 10 digits |
| `kod_audi` | string | Unused. **Discarded at ingestion (3.5)** | always empty |
| `dealer`, `dealer_nr` | string | Dealer name and number; kept in the private repository only | 38 dealers; `90006` = “Dostępny na terenie całego kraju” |
| `telefon` | string | Dealer phone. **Discarded at ingestion (3.5)** | one per dealer |
| `cena_katalogowa` | numeric string | Catalog price, PLN gross | 136,700 – 1,158,240 |
| `cena_vtp` | numeric string | Special price (“cena specjalna”), PLN gross | empty for 2 cars |
| `cena_historyczna` | numeric string | Lowest price in the 30 days before the reduction | always present |
| `cena_historyczna_katalogowa` | numeric string | Catalog price 30 days before | differs from `cena_historyczna` for 2,580 cars |
| `rata` | numeric string | Audi Perfect Lease monthly rate, PLN net, for businesses | empty for the same 2 cars |
| `stara_rata`, `rata_historyczna` | numeric string | Previous rate; lowest rate in the 30 days before | `stara_rata` empty for 2,619 cars |
| `rok_produkcji` | string | Production year | 2026 (4,766), 2025 (2) |
| `rok_modelowy` | string | Model year (“rocznik”) | 2025 (899), 2026 (2,378), 2027 (1,491) |
| `kod_modelowy` | string | 6-character model code, drives most badge rules | e.g. `8YFBNG`, `4MQCN2` |
| `id` | string | `rok_modelowy + rok_produkcji + kod_modelowy`, not unique | e.g. `202620268YMANG` |
| `business_edition` | `Tak` or `Nie` | Business Edition flag | 2,847 Tak |
| `stock_cleaning` | `Tak` or `Nie` | Clearance flag; feeds the best-offer and insurance rules | 1,911 Tak |
| `moj_elektryk` | `Tak` or `Nie` | Subsidy programme flag | always Nie |
| `link` | URL | audi.pl offer page. **Discarded at ingestion (3.5)** | one per item |

All numeric fields arrive as strings; empty string means null. The redacted item is archived in `raw/` and the typed offer in `snapshots/`, both in the private repository.

### 3.4 Promo sliders and card badges

| Promo (site wording) | Slider request | Card badge rule in `main.js` (rules v1, valid from 2026-10-13) | Count 13 Oct 2026 |
|---|---|---|---|
| Najlepsza oferta z rocznika 2026 | `bo=Tak` | model code not starting with `8YFRWY`, `8YMRWY`, `8YV`, `8YY`, `8YW`, and (`stock_cleaning=Tak` or code starts with `8YF`, `8YM`, `8YJ`, `4MQ`) | 2,347 (slider = badge) |
| Audi Q7 Final Edition | `m[]=Audi Q7&m[]=Audi Q7 TFSI e&m[]=Audi SQ7&mc[]=4MQ*&rm=2026` | model in that trio, code starts with `4MQ`, `rok_produkcji=2026`; replaces the Business Edition badge on the card | 230 |
| Leasing 101% | `l101badge=Tak` | `rok_produkcji=2025` and model in the Q5 family, or `rok_produkcji=2026` and model in the 53-name list in the bundle | 4,675 slider, 4,676 badge (RS e-tron GT performance is the odd one) |
| Pakiet ubezpieczeń za 1 zł | `pu=Tak` | package type: insurance+service = Q5 family and 2025; insurance-or-service = (Q5 family, `stock_cleaning=Tak`, 2026) or A6 Limousine / Avant incl. e-hybrid with code `FN2` or `FN5` and 2026; insurance-only = Q7 trio with `4MQ` and 2026 | 1,916 (slider = badge) |
| Oferta Business Edition | `b=Tak` | `business_edition=Tak`; the slider also returns Final Edition cars whose card shows only the Final Edition badge | 2,847 |
| Dodatkowe 15 000 zł korzyści | no slider | A6 e-tron family (code `GH`) or Q6 e-tron family (code `GF`), `rok_produkcji=2026` | 81 (badge only) |

Rate footnote shown next to the monthly rate: `2` if the model name contains `e-tron`; `3` if (Q5 and code `GU`) or (Q7 and code `4MQ`) or A3 / S3 with codes `8YM`, `8YF`, `8YJ` or any code starting with `4MT`, `FJ`, `FU`, `FN`, `4N`; otherwise `1`. The footnotes define the plan assumptions in section 6.

Q5 family = Audi Q5, Q5 e-hybrid, Q5 Sportback, Q5 Sportback e-hybrid, SQ5, SQ5 Sportback. The full 2026 Leasing 101% model list and both e-tron family lists are copied into `rules/promo_rules.yaml` from the bundle.

Per-offer promo flags come from the badge rules above, because joining a slider response to the main pull would need an identifier. Slider responses are used only as counts per model: they keep the site’s own filter numbers visible in the trends and cross-check the badge rules (4.3).

### 3.5 Fields discarded at ingestion

The collector removes five fields from every item of every response right after schema validation, before anything is written to disk, logged or passed to normalisation. No hash, prefix or other derivative of them is kept.

| Field | Why it is dropped |
|---|---|
| `vin` | Identifies one vehicle and can become personal data once the car is registered to a person; trends do not need it |
| `komisja` | Dealer stock number; with `dealer_nr` it addresses a single offer |
| `link` | Direct link to a single offer on audi.pl |
| `kod_audi` | Always empty; dropped to keep the stored schema minimal |
| `telefon` | Dealer phone number; not needed |

Slider responses are reduced to item counts per `model` in memory; their items are never stored. The collector’s offer type has no attribute for any dropped field, a unit test feeds items with all five and asserts that no output contains them, and the identifier check of 10.5 fails a run on any VIN-shaped string in either repository’s `data/`. Without an identifier an offer cannot be followed from one run to the next; everything that compares runs works on configurations (5.1, 5.5).

### 3.6 Behaviour to expect

- No cookies, tokens or headers are required; the cookie banner is client-side only.
- Responses are not cached (`Cache-Control` absent); counts can change between two calls in the same run, so the main pull is the record and the slider counts are a cross-check only.
- The bundle name changes on every site deploy; when the hash changes a person reads the rules from the live site (runbook). The bundle is never parsed automatically, downloaded or archived.
- On 13 Oct 2026 the subdomain had no `robots.txt` and no text-and-data-mining reservation (no `/.well-known/tdmrep.json`, no `tdm-*` headers, no robots meta tag); `www.audi.pl/robots.txt` disallows only `/userinfo/`. The runbook repeats this check at every rules review; a reservation found later stops collection until the owner decides (11, Legal).

Sources: gotowedoodbioru.audi.pl, bundle `main.20ab651335fb4daeebc8.js` (760 kB, 13 Oct 2026), Regulamin of audi.pl (Volkswagen Group Polska sp. z o.o., read 13 Oct 2026).

## 4. Collector

A Python package (`collector/`, in the public repository) that one GitHub Actions job in the private repository runs every week; a run makes at most 10 HTTP requests, writes one redacted snapshot and the private derived files into the private repository, and pushes the aggregate files to the public repository.

### 4.1 Schedule

- Workflow `collect.yml` in the private repository: cron every Monday 05:17 UTC plus `workflow_dispatch` with inputs `force` (ignore the 6-day guard) and `date` (override the snapshot date, for replays).
- The job exits early with status `skipped` when the newest snapshot in `data/snapshots/index.json` is younger than 6 days (`min_snapshot_age_days`). Result: one snapshot every Monday; a forced run on another weekday makes the job skip a Monday that falls within 6 days of it.
- `concurrency: collector` so two runs never overlap; job timeout 15 minutes.

### 4.2 Steps of a run

1. `GET /` and read the `main.<hash>.js` name; record the hash in the run report and `data/meta/bundles.json`. The bundle itself is never requested.
1. `GET data_models2.json` and `data_dealers2.json`; refresh `data/meta/models.json` and `data/meta/dealers.json` (number, name and city; new dealers appended, nothing deleted); run the model lifecycle of 4.6.
1. `GET get2.php?p=1&c=20000&s=price&d=asc`; retry 3 times with 10 s, 30 s, 90 s back-off (retries are not counted against the request budget, ADR-0005); fail the run if `count` differs from `len(items)` after retries.
1. Validate every item against the schema in 3.3 (pydantic). Unknown fields are kept in `extra`; a missing known field fails the run.
1. Redact: drop the fields of 3.5 from every item. No later step can see them.
1. `GET` the five slider sets from 3.4 and `pks=Tak`, each with `c=20000`; keep only the number of items per model.
1. Normalise: types, empty string to null, badge bits from `rules/promo_rules.yaml`, `plan_code` from `rules/plans.yaml`, `discount`, `discount_pct`, `config_key`, `version_key`, canonical order and `offer_id` (section 5).
1. Compare with the previous `ok` snapshot at configuration and model level (6.2).
1. Compute analytics (section 6); rebuild every private derived file under `data/private/` and the public tree under `data/public/`.
1. Write `data/exports/<date>.xlsx` and `latest.csv`; write `data/reports/<date>.md`.
1. Run the publication guard on `data/public/` and the identifier check on all of `data/`, exports and report included (10.5); a failure fails the run before anything is committed or pushed.
1. Commit `data/` to the private repository as `data: snapshot <date> (<n> offers, <m> models)`; mirror `data/public/` onto the public repository’s `data/` (files no longer in `data/public/` are deleted there) and push it as `data: trends <date>`, which triggers the Pages deploy.

Requests carry `User-Agent: audilitics/<version> (price trend research; +https://github.com/rlgdev/audilitics)` and are spaced 1 s apart. The ten budgeted requests are the index page of step 1, the two directories of step 2, the main pull of step 3 and the six slider pulls of step 6.

### 4.3 Quality gates

| Condition | Snapshot status | Action |
|---|---|---|
| Count within ±20 % of the previous run and schema valid | `ok` | Normal processing |
| Count below 80 % of the previous run | `suspect` | Stored in the private repository; excluded from trends, scoring and every public figure until a maintainer sets `ok` in `index.json`; issue `collector-failure` |
| Count above 120 % of the previous run | `ok` with warning | Included; warning in the report |
| Schema change: new field | `ok` with warning | Field kept in `extra` unless it looks like an identifier or a URL, in which case it is dropped and listed in the report; issue `schema-change` |
| Schema change: known field missing, or JSON parse error | `failed` | No snapshot written; issue `collector-failure` |
| HTTP 403 or 429 | `failed` | Stop immediately, no retry storm, no workaround; issue `collector-blocked` |
| Slider count of a promo differs from its badge count by more than 1 % in total | `ok` with warning | Warning in the report; issue `rules-review` |
| Bundle hash changed | unchanged | Issue `rules-review` listing the rules in 3.4 to re-verify |
| Publication guard or identifier check fails (10.5) | `failed` | Nothing committed or pushed; issue `publication-guard` with the findings |

Issues are created in the private repository with the GitHub CLI inside the job; an existing open issue with the same label is updated, not duplicated.

### 4.4 Commands

- `make collect DATA=<dir>` — full run against the live site into a private data directory (`../audilitics-private/data` locally, the checkout in CI).
- `make collect FROM=<dir>/raw/2026-10-27.json.gz` — replay a run from an archived redacted raw file (rebuilds every derived file for that date).
- `make rebuild DATA=<dir>` — replay all raw files in order; used after a rules or scoring change.
- `make collect FIXTURE=1` — run against the synthetic fixture of the public repository (`collector/tests/fixtures/synthetic/`) without network; `FIXTURE=real` runs against the redacted 13 Oct 2026 fixture of the private repository.
- `make guard` — run the publication guard of 10.5 on a public tree (`data/public/` of a private data directory, or `data/` of the public repository).
- `make test` — unit and contract tests (section 12).

### 4.5 Configuration

| File | Holds |
|---|---|
| `collector/config.yaml` | Base URL, page size, request budget, back-off, thresholds of 4.3, User-Agent, `discarded_fields` (3.5), `public_min_group: 3` (5.5), public repository name |
| `rules/promo_rules.yaml` | Slider parameters, badge rules and model lists of 3.4, each rule set with `valid_from` |
| `rules/plans.yaml` | Footnote to plan mapping of section 6 (`APL-1`, `APL-2`, `APL-2-EV`, `APL-3`) |
| `rules/scoring.yaml` | Deal-score weights, caps and hot thresholds of section 6 |
| `rules/models.yaml` | Overrides only: segment or display-order exceptions and manual retirements; the model list itself is discovered from the feed (4.6) |

A snapshot is always processed with the rule set valid on its date, so a rule change never rewrites history unless `make rebuild` is run on purpose.

### 4.6 Model lifecycle

The set of models is read from the feed on every run, never from a hand-written list, so a new model shows up in the dashboard on the run it first appears and a discontinued one retires on its own.

| Event | Detection | Action |
|---|---|---|
| New model | A `model` value in `get2.php` items or in `data_models2.json` that is not in `meta/models.json` | Add it with `first_seen` = run date, status `active`, a slug from the name (`Audi Q6 Sportback e-tron` → `q6-sportback-e-tron`), a segment from the name rules below, and a display order after the last model of the same segment; listed under “new models” in the run report and in the Changes view |
| New engine group or dealer | A `silnik2` or `dealer_nr` value not seen before | Appended to the directories (dealers in the private repository only); an engine group takes the next free colour slot in its model (8.2) |
| Model with zero cars | No item with that `model` in an `ok` snapshot | `empty_runs` incremented; stays `active` |
| Retire | `empty_runs` reaches 3 (about six weeks) | Status `retired`, `retired_on` = run date; hidden from the model board and filters by default, kept in trends, Changes and the Model page; listed under “retired models” |
| Return | A retired model appears again | Status `active` again, `empty_runs` reset, keeps its slug and history |
| Renamed model on the site | A new name whose cars carry the model-code prefix (first three characters of `kod_modelowy`) of a retired or empty model | Added as a new model and flagged `possible_rename_of` in the report; a maintainer may merge the two in `rules/models.yaml` |

Segment from the name: S / RS when the name starts with `Audi RS`, or with `Audi S` followed by a digit or `Q`; e-tron when it contains `e-tron`; Q when it starts with `Audi Q`; otherwise A. `rules/models.yaml` can override segment, order, slug and status for any model; overrides win over discovery.

The retirement threshold (`empty_runs: 3`) lives in `collector/config.yaml`. A model retired by mistake is reactivated by the next run that lists cars for it, so the rule is safe to leave automatic.

## 5. Data model and file layout

An offer is one redacted item of one snapshot and has no identity outside it. The configuration (model + engine + model code + model year) is the unit compared across runs and the unit of publication. Offer-level files live in the private repository; aggregate files are written to `data/public/` and pushed to the public repository.

### 5.1 Entities

| Entity | Key | Holds | Where |
|---|---|---|---|
| Snapshot | `date` (ISO, one per run) | status (`ok`, `suspect`, `failed`), counts, bundle hash, rules version, duration | Private; the public index lists its date and status (5.5) |
| Offer | `offer_id` = `<date>/<n>` (5.5) | The redacted, normalised item of 3.3 plus derived fields (5.2) | Private |
| Configuration | `config_key`, computed exactly as in release 1.0 (`normalise.py`, ADR-0006): first 16 hex characters of sha1 over `model`, `engine` (from `silnik`), `code`, `model_year` | Label, model slug, engine group, plan code, per-snapshot aggregates: offers, prices, discount, rate, badge counts, score summary | Public on a date when it has at least 3 priced offers (5.5); private otherwise |
| Version | `version_key`, computed as in release 1.0: first 16 hex characters of sha1 over `model`, `engine`, `code`, `model_year`, `catalog`, `special`, `price_30d`, `rate`, `promo_bits` (badge bits only from 1.1) | Identical offers (`identical` count) | Private |
| Model | `slug` (e.g. `q5-sportback-e-hybrid`) | Display name, slug, order, segment, status (active or retired), first_seen, last_seen, retired_on, empty_runs, engine groups, per-snapshot aggregates | Public |
| Dealer | `dealer_nr` | Name and city (parsed from the name where possible); no phone | Private |
| Rule set | `valid_from` | Promo, plan and scoring rules applied to snapshots from that date | Public (`rules/`) |

### 5.2 Derived fields on an offer

| Field | Definition |
|---|---|
| `catalog`, `special`, `price_30d`, `catalog_30d`, `rate`, `rate_old`, `rate_30d` | Typed copies of the feed fields; null when empty |
| `discount` | `catalog - special` |
| `discount_pct` | `discount / catalog`, 4 decimals |
| `promo_bits` | Badge bits with the positions of release 1.0: 5 best offer, 6 +15 000 zł, 7 Leasing 101%, 8 insurance, 9 Business Edition, 10 Final Edition. Slider bits 0–4 and 11 are no longer set on offers, because slider membership would need an identifier |
| `package_type`, `footnote`, `plan_code` | Insurance package type, rate footnote and plan code from the rules of 3.4 and section 6 |
| `config_key`, `version_key` | As in 5.1 |
| `config_change` | Median special price of the offer’s configuration minus the same median in the previous `ok` snapshot; null when the configuration is new there |
| `lowest_ever` | `true` when `special` is not null and not above the lowest `special` seen for this `config_key` across all `ok` snapshots |

### 5.3 Files

Private repository `rlgdev/audilitics-private`:

```text
data/
  raw/<date>.json.gz              redacted feed items, slider counts per model, models and dealers JSON, selected headers, request log
  snapshots/<date>.json.gz        normalised offers of one date in canonical order
  snapshots/index.json            [{date, status, offers, models, configurations, dealers, bundle_hash, rules_version}]
  private/models/<slug>.json      per model: current offers (offer table) and every configuration with its full history
  private/deals.json              scored current offers with the score breakdown; rankings by offer_id
  private/dealers.json            per dealer per snapshot: offers, median discount_pct, models now
  public/                         the public tree below, byte-identical to what is pushed
  meta/models.json, meta/dealers.json, meta/bundles.json
  exports/<date>.xlsx, exports/latest.csv
  reports/<date>.md               run report: counts, gates, guard result, warnings, request log
fixtures/2026-10-13/raw.json.gz   redacted real feed for the acceptance tests of 12.1
```

Public repository `rlgdev/audilitics`:

```text
data/                             written only by the collector job (pushed from the private repository)
  manifest.json                   latest snapshot date and file hashes
  snapshots/index.json            [{date, status, offers, models, configurations, rules_version, bundle_hash}]
  dashboard/latest.json           KPIs, model tiles, hot deals (configurations), changes summary, directory (segments, engine groups,
                                  plans, promos, scoring parameters; no dealers) - the only file the Overview needs
  dashboard/trends.json           totals, segments and models per snapshot: count, min/median/max special, median discount_pct,
                                  min/median rate per plan, badge counts, slider counts, net added and removed, like-for-like index
  dashboard/changes/<date>.json   configuration and model changes against the previous ok run
  dashboard/deals.json            every published configuration with its score summary and hot fields, plus the rankings
  models/<slug>.json              per model: timeline, engine-group series, configurations (≥ 3 priced offers) with their history
  meta/models.json                model directory
collector/tests/fixtures/synthetic/   generated offers with invented prices and dealer names for CI; no real data
```

### 5.4 Sizes and budgets

| File | Size per run (13 Oct 2026 volume, estimate) | Read by |
|---|---|---|
| private `raw/<date>.json.gz` | ~300 kB | collector replay only |
| private `snapshots/<date>.json.gz` | ~250 kB | collector; private Car page |
| private `private/deals.json` | ~1 MB | private Offers page |
| public `dashboard/latest.json` | ~40 kB | Overview, first request |
| public `dashboard/trends.json` | ~2 kB per snapshot per model | Overview charts, Model page |
| public `dashboard/deals.json` | ~150 kB | Best deals |
| public `models/<slug>.json` | 2–60 kB each | Model page, on demand |

A year of weekly runs adds about 30 MB to the private repository and under 10 MB to the public one; nothing is pruned in release 1.1. Files the browser reads are stored uncompressed because GitHub Pages compresses text responses itself; archives stay gzipped.

### 5.5 Identity and publication rules

- An offer exists only inside its snapshot. `offer_id` = `<date>/<n>`, where `n` is the 1-based position in the canonical order: `model`, `engine`, `code`, `model_year`, `special` (nulls last), `catalog`, `rate`, `dealer_nr`, `promo_bits`, then feed order. The same car on two dates has two unrelated ids.
- Runs are compared through configurations matched by `config_key`: counts and median prices are compared, never individual offers.
- Minimum group size (`public_min_group: 3`): apart from counts of offers, every public figure rests on at least 3 offers of that snapshot, and every price, rate, discount or score figure on at least 3 priced offers. Each public group carries `offers` and `priced` next to its statistics (rates: the count per plan), so the guard can check them. Below the threshold a configuration has no public row on that date (its offers still count in model, segment and total counts); a model, segment, engine group or plan group shows its count of offers and nothing else.
- Public files hold no offer-level row, no `offer_id`, no dealer name or number, no URL to audi.pl, no field of 3.5 and no score components of a single offer.
- A `suspect` snapshot is excluded from every public figure; the public index lists its date and status only, so the dashboard can warn.
- Dates are the run date in UTC; the dashboards show them in Europe/Warsaw.

## 6. Analytics

All figures below are computed in the collector from `ok` snapshots: configuration, model, segment and total aggregates go to the public tree, offer-level scores to `data/private/`; the dashboards never recompute them. Offers without a special price are excluded from price statistics and scoring but stay in counts. Every public figure obeys the minimum group size of 5.5.

### 6.1 Trends per model (and per segment, engine group and configuration)

| Measure | Definition per snapshot |
|---|---|
| `count` | Offers in stock |
| `special_min`, `special_median`, `special_max` | Over `special`; null below the minimum group size |
| `discount_pct_median` | Over `discount_pct`; null below the minimum group size |
| `rate_min`, `rate_median` | Over `rate`, per `plan_code` (a 24-month rate is never pooled with a 36-month rate), each plan with its own count; null below 3 priced offers in that plan |
| `promo_counts` | Offers per badge: best offer, Final Edition, Leasing 101%, insurance, Business Edition, +15 000 zł; null below 3 offers |
| `slider_counts` | Items per slider request, keyed as in `rules/promo_rules.yaml`: `bo` (`bo=Tak`), `fe` (the Q7 Final Edition request), `l101` (`l101badge=Tak`), `pu` (`pu=Tak`), `be` (`b=Tak`), `pks` (`pks=Tak`); the site’s own filter numbers; models, segments and totals only; null below 3 |
| `net_added`, `net_removed` | Sum over the model’s configurations of the positive and of the negative change in count against the previous `ok` snapshot (removed as a positive number). A lower bound of real turnover: a sold car replaced by an identical one is invisible |
| `lfl_index` | Like-for-like price index over matched configurations: median of `special_median_t / special_median_t-1` over configurations with at least 3 priced offers in both snapshots, chained from the first snapshot = 100; a step with no matched configuration keeps the index flat |
| `lowest_version_special` | Lowest `special_min` of the model across all `ok` snapshots so far; models only |

Engine-group series in `models/<slug>.json` carry `count`, `priced`, `special_min` and `special_median` under the same rules. The Overview also carries totals over all models: `count`, `special_median`, `discount_pct_median`, `rate_min` (with its model and plan), `promo_counts`, and the number of configurations whose median price fell.

### 6.2 Changes between consecutive snapshots (`dashboard/changes/<date>.json`)

| List | Entry |
|---|---|
| `configs_new` | Configurations published now (5.5) and not published in the previous snapshot: label, model, engine group, offers, median special, best score, and `reason` (`new_in_stock` or `reached_minimum`) |
| `configs_gone` | Configurations published in the previous snapshot and not now: label, model, last median special, and `reason` (`none_left` or `below_minimum`) |
| `price_drops`, `price_rises` | Configurations published in both snapshots: previous and new median special, difference, %, offers now, consecutive drops of the median |
| `stock` | Per model: offers before and now, `net_added`, `net_removed` |
| `promo_changes` | Per model: badge counts before and now, for badges whose count changed |
| `summary` | Count of each list, median configuration drop %, largest configuration drop (label, difference, %), models with the most net additions |
| `models_new`, `models_retired`, `models_returned` | model, slug, segment, offers now, first or last seen (4.6) |

The Changes page compares a run with the run before it; there is no free choice of pairs.

### 6.3 Deal score (0–100, per offer, summarised per configuration)

| Component | Weight | Definition (percentiles are within the same model unless stated) |
|---|---|---|
| Discount depth `D` | 35 | Percentile rank of `discount_pct` |
| Price position `P` | 25 | 100 minus the percentile rank of `special` within the same model and engine group |
| Momentum `M` | 20 | Fall of the offer’s configuration median special since the previous `ok` snapshot: 0 % → 0, 5 % or more → 100, linear between; a configuration that is new, or had fewer than 3 priced offers before, scores 50 |
| Rate value `R` | 10 | 100 minus the percentile rank of `rate / special` within the same model and `plan_code` |
| Promo bonus `B` | up to 10 | Insurance for 1 zł +4, Final Edition or +15 000 zł badge +4, best-offer badge +2 |

`score = 0.35 D + 0.25 P + 0.20 M + 0.10 R + B`, rounded to an integer. Weights and the 5 % momentum cap live in `rules/scoring.yaml`; every offer in `private/deals.json` carries the five component values so the private UI can show the breakdown.

Configuration summary (public, for published configurations): `score_best` (highest offer score), `score_median`, the medians of the five components (`D`, `P`, `M`, `R`, `B`; they do not add up to the median score), `offers_80` (offers scoring 80 or more), `offers`, `priced`, `catalog_median`, `special_min`, `special_median`, `price_30d_median`, `discount_pct_median`, `discount_pct_max`, `rate_min` and `plan_code`, `initial_fee` (plan fee on `catalog_median`), `term`, badge counts. No single offer’s components are published.

Configuration flags: `lowest_ever` (`special_min` not above the lowest ever seen for the configuration), `biggest_drop_this_run` (largest median drop % in its model), `new_config` (first `ok` snapshot in which it is published). Offer flags (private): `lowest_ever` (5.2), `last_one` (only offer of its version).

`deals.json` holds every published configuration with its summary, flags and hot fields (6.5). Rankings written per run, public: top 50 configurations overall, top 3 per model, top 10 per segment (A, Q, S / RS, e-tron), ordered by `score_best`, then `score_median`, then larger `discount_pct_median`. Private: the same three rankings of offers, ordered by score, then larger `discount`, then `offer_id`.

### 6.4 Payment-plan assumptions behind the rate

The site shows one Audi Perfect Lease rate per car (net, businesses, calculated from the catalog price). The footnote the site assigns (3.4) selects the plan; the dashboard shows these values next to every rate and in the About page.

| Plan code | Footnote | Initial fee (of catalog price) | Term | Mileage per year |
|---|---|---|---|---|
| `APL-1` | 1 | 10 % | 36 months | 15,000 km |
| `APL-2` | 2 | 10 % | 24 months | 15,000 km |
| `APL-2-EV` | 2, exception | 8 % | 24 months | 15,000 km — electric models of model year 2026 and the A6 e-tron / Q6 e-tron ranges |
| `APL-3` | 3 | 10 % | 24 months | 15,000 km |

Derived for display only: `initial_fee = fee_pct × catalog`, `rate_total = rate × term`. Leasing 101 % (25 % initial fee, 24 months, 20 % residual) is a flag, not a rate, and is shown as a chip with its footnote text.

### 6.5 Hot deals of the last month

A hot deal is a configuration in stock today, with at least 3 priced offers, whose price got clearly better within the last 31 days; the collector writes the ranked list into `latest.json` so the main screen shows it without any further request.

| Rule | Definition |
|---|---|
| Window | All `ok` snapshots dated within the last 31 days, including the current one (normally two or three runs) |
| Price points | `(date, median special)` of the configuration in every window snapshot where it had at least 3 priced offers; the first point is the start price |
| Qualifies | At least one of: median special fell by 3 % or more, or by 5,000 PLN or more, against the start price; `special_min` reached the configuration’s lowest ever inside the window after a fall; first published inside the window (not on the first `ok` snapshot ever) with `score_best` of 80 or more |
| Hot score | `score_best` + min(20, 4 × drop in percent), where drop in percent = 100 × (start price − median special now) / start price, and 0 when the price did not fall; rounded to 1 decimal |
| Output | `latest.json.hot_configs`: up to 24 configurations ordered by hot score, then drop amount, then label; each with label, model, slug, segment, engine group, model year, offers, median special, start price, drop amount and %, `score_best`, flags, reasons, badge counts and the price points. Every configuration in `deals.json` also carries `hot` and `hot_score` |
| Deals page | Filter `hot=1` lists every configuration with `hot: true` in `deals.json`, in hot-score order (not only the 24 in `latest.json`); in the private build, Offers with `hot=1` lists the offers of hot configurations |
| Thresholds | `hot_window_days: 31`, `hot_drop_pct: 0.03`, `hot_drop_pln: 5000`, `hot_new_score: 80` in `rules/scoring.yaml` |

With a single snapshot nothing qualifies and the panel shows its empty state.

## 7. Dashboard

One app, two builds. The public build (`EDITION=public`) has five routes and reads only the public tree; the private build (`EDITION=private`) adds three routes for offers and dealers and runs only on the owner’s machine. One filter row scopes everything below it, and every view is addressable by URL. The Overview is the hero: a board of all 53 models with a price sparkline each, in the order the site lists them.

### 7.1 Routes

| Route | Build | Purpose | Data read | Content |
|---|---|---|---|---|
| `#/` Overview | both | Stock at a glance and what moved | `latest.json`, `trends.json` | Freshness line (snapshot date, next run, status); KPI row: offers in stock with delta vs previous run, models, median discount %, lowest rate (with model and plan), configurations with a price drop; “Hot deals of the last month” panel of up to 8 configuration cards right under the KPI row (7.6); two small trend charts (offers over time; median special price over time); the model board: one tile per active model with count, delta, lowest special price, median-price sparkline, promo chips; “What changed this run” panel (net additions and removals, configurations with price drops, new and retired models) with links to Changes |
| `#/model/:slug` Model | both | One model over time and its configurations now | `models/<slug>.json` | Header with count, price range, rate range, engine groups; trend chart: median special price line with min–max band per snapshot, like-for-like index as a second small chart; engine small multiples (one line per engine group, legend + direct labels); promo mix bars per snapshot; configuration table (7.3) with a drawer per configuration. The private build adds an Offers tab with the offer table |
| `#/deals` Best deals | both | Ranked configurations | `deals.json` | Ranked configuration table with best and median score, breakdown popover of the median components, flags, promo chips with counts; toggle “top 3 per model”; segment tabs; `hot=1` filter |
| `#/changes` Changes | both | What changed between a run and the run before | `changes/<date>.json` | Run picker (default: latest); summary tiles; tabs: new configurations, gone configurations, price drops, price rises, stock by model, promo changes |
| `#/about` About | both | Methodology and data notes | `latest.json`, static text | Plan assumptions (6.4), promo definitions (3.4), score definition (6.3), what is not collected and the minimum group size (3.5, 5.5), rules version, last run summary; the source named as plain text without a link; notice that the figures are aggregates of offers published on the source site, not offers within the meaning of the Civil Code, and that the project is not affiliated with Audi or Volkswagen Group Polska |
| `#/offers` Offers | private | Ranked offers | `private/deals.json` | Offer table (7.3) with score, breakdown popover, flags, promo chips; segment tabs; `hot=1` lists the offers of hot configurations |
| `#/dealers` Dealers | private | Who has stock and who discounts most | `private/dealers.json` | Table dealer × offers × median discount %, sortable; small multiples of offers per dealer over time |
| `#/car/:date/:n` Car | private | One offer on one date | `snapshots/<date>.json.gz` (decompressed in the browser), `private/models/<slug>.json` | Attributes, prices, rate and plan, badges, score breakdown, dealer, identical offers, and the median-price history of its configuration; no link to audi.pl |

The public build contains no route, fetch or component for the private files; `#/offers`, `#/dealers` and `#/car/...` show the not-found state there.

### 7.2 Filter row (all pages except Car and About)

| Control | Options | Default |
|---|---|---|
| Period | Last 3 months, 6 months, 12 months, all | All (until 12 snapshots exist) |
| Segment | A (A3–A8), Q, S / RS, e-tron, all | All |
| Model | Multi-select, grouped by segment | All |
| Engine group | Multi-select (`silnik2`) | All |
| Dealer | Multi-select; private build only | All |
| Promo | Multi-select of the six badges | None |
| Plan | `APL-1`, `APL-2`, `APL-2-EV`, `APL-3` | All |

What each filter scopes: Period, Segment and Model apply everywhere. On the Overview the KPI row and the two trend charts show totals, or one segment’s series when exactly one segment is selected; they are never recombined from finer groups. Engine group, Promo and Plan filter configuration rows only (configuration tables, Best deals, hot cards, Changes lists) and the engine-group lines on the Model page. In the private offer table every filter applies per offer and the selected badges combine with AND, like the site; in configuration rows a configuration matches when each selected badge is carried by at least one of its offers. Filters live in the query string (`#/deals?segment=q&promo=l101,pu`), so a filtered view is a shareable link and the browser back button works. Changing a filter re-renders every chart and table on the page; during a data fetch the previous render stays at reduced opacity.

### 7.3 Tables

Configuration table (both builds; Model and Best deals): model, engine, model code, model year, offers, catalog price (median), special price (min and median), discount % (median and max), 30-day price (median), promos (badge chips with counts), rate from and plan, initial fee (on the median catalog price), term, best score, median score, flags. Row click opens the configuration drawer.

Offer table (private build only; Offers page and the Offers tab of Model), mirroring the 13 Oct workbook without identifiers: model, engine, model code, model year, catalog price, special price, discount, discount %, 30-day price, promos, rate, plan, initial fee, term, identical offers, dealer, score. Row click opens the Car page. There is no VIN or link column.

Both: column chooser, column sort, sticky header, virtualised rows, `pl-PL` number formatting (space thousands, `zł`), CSV export of the current view.

### 7.4 Components

| Component | Contract |
|---|---|
| `FreshnessBar` | Snapshot date, next scheduled run, status; shows a warning strip when the newest snapshot is older than 9 days or `suspect` |
| `KpiTile` | label, value (auto-compact), delta vs previous run with direction, optional 12-point sparkline |
| `ModelTile` | model name, count, delta, lowest special price, sparkline, up to three promo chips, link to Model |
| `TrendChart` | ECharts line; crosshair with a tooltip listing every series at that date; one y-axis; 2 px lines; 8 px end markers; legend when 2+ series |
| `RangeChart` | Median line with min–max band at ~10 % opacity |
| `PromoMixChart` | Stacked bars per snapshot, one fixed colour per promo, 2 px surface gaps |
| `PromoChip` | Site wording verbatim, fixed colour per promo, tooltip with the footnote text; optional count |
| `ScoreBreakdown` | Popover with the five components and the formula; for a configuration it shows the median components next to the best and median score, noting that medians do not add up |
| `DataTable` | TanStack Table wrapper: columns, sorting, chooser, virtualisation, CSV export |
| `RunPicker` | One dropdown of `ok` snapshots for the Changes page; each is compared with the run before it |
| `ConfigDrawer` | Side panel with the configuration’s median-price line and min–max band over its published snapshots, offers count, badge mix |
| `ThemeToggle` | Light, dark, system |
| `EmptyState`, `ErrorState` | Plain-language text with the action that fixes it (“No configurations match these filters. Clear filters”) |
| `HotConfigCard` | model, engine and model year, offers, median special price, drop inside the window (amount and %, down-arrow icon, good colour, label), best score, up to two promo chips, sparkline of the window’s median-price points; the whole card links to `#/model/:slug?config=<config_key>` |

### 7.5 Behaviour

- Hash router (`react-router` hash history) so deep links work on GitHub Pages without a 404 fallback.
- `VITE_EDITION` (`public` or `private`) selects the routes in one routes module at build time. The public build fetches only `<base>/data/...`. The private build reads one private checkout given by `VITE_DATA_BASE`: public files from `<VITE_DATA_BASE>/public/`, private files from `<VITE_DATA_BASE>/private/`, snapshots from `<VITE_DATA_BASE>/snapshots/`.
- Data is cached per snapshot date in memory; nothing is stored in `localStorage` except theme and column choices.
- All strings from the feed (engine strings, model names, dealer names in the private build) are inserted as text, never as HTML.
- No outbound links: neither build renders a link to audi.pl or to any page of the source; the source is named as plain text in About.
- Numbers: `Intl.NumberFormat('pl-PL')`; dates: `13 paź 2026` style via `Intl.DateTimeFormat('pl-PL')`; UI labels in English.
- Responsive to 375 px: filter row wraps, tables switch to card rows, charts keep the crosshair.
- Keyboard: every control reachable, visible focus ring, tooltips also on focus; `prefers-reduced-motion` disables the single page-load reveal.

Retired models (4.6) are hidden from the model board and the model filter by default; a “Show retired models (n)” toggle in the filter row reveals them, their Model pages stay reachable by URL, and the Changes view lists retirements and returns.

### 7.6 Hot deals of the last month

- Position: directly under the KPI row on the Overview, above the trend charts, so it is the first content a reader sees after the headline numbers.
- Header: “Hot deals of the last month”, the window dates (`16 wrz – 13 paź 2026`), and a “See all (n)” link to `#/deals?hot=1`.
- Body: up to 8 `HotConfigCard`s from `latest.json.hot_configs`, in hot-score order; one row on desktop, two rows at 1024 px and below, a horizontally scrollable row on phones.
- Filters: the segment, model, engine-group and promo filters of 7.2 apply to the panel; the period filter does not (the window is fixed by 6.5).
- Empty state: “Hot deals appear after the second collection run.”, or “No hot deals match these filters. Clear filters” when filters hide them all.
- Card motion: none on load; a card lifts only on hover and focus.

## 8. Visual design system

The dashboard reuses the validated reference palette and chart rules of the `dataviz` skill unchanged, and the design process of the `frontend-design` skill; both are bundled with Claude and their reference files are copied into `docs/design-system.md` so the rules travel with the repository.

### 8.1 Tokens (`web/src/styles/tokens.css`)

| Role | Light | Dark |
|---|---|---|
| Page plane | `#f9f9f7` | `#0d0d0d` |
| Chart and card surface | `#fcfcfb` | `#1a1a19` |
| Primary ink | `#0b0b0b` | `#f0efec` |
| Secondary ink | `#52514e` | `#c3c2b7` |
| Muted (axis, labels) | `#898781` | `#898781` |
| Gridline (1 px solid) | `#e1e0d9` | `#2c2c2a` |
| Baseline / axis | `#c3c2b7` | `#383835` |
| Border ring | `rgba(11,11,11,0.10)` | `rgba(255,255,255,0.10)` |
| Accent (links, selection) | `#2a78d6` | `#3987e5` |
| Good (price went down) | `#006300` text, `#0ca30c` icon | `#0ca30c` |
| Critical (price went up, failed run) | `#d03b3b` | `#d03b3b` |
| Warning (suspect snapshot, stale data) | `#fab219` | `#fab219` |

Dark mode is a selected set, declared under both `@media (prefers-color-scheme: dark)` and `:root[data-theme="dark"]`, with the toggle winning.

### 8.2 Categorical colours — fixed, never cycled

| Slot | Light | Dark | Assigned to |
|---|---|---|---|
| 1 blue | `#2a78d6` | `#3987e5` | The selected or primary series (a model’s median price, the stock count); promo “Najlepsza oferta z rocznika 2026” |
| 2 orange | `#eb6834` | `#d95926` | Promo “Audi Q7 Final Edition” |
| 3 aqua | `#1baf7a` | `#199e70` | Promo “Leasing 101%” |
| 4 yellow | `#eda100` | `#c98500` | Promo “Pakiet ubezpieczeń za 1 zł” |
| 5 magenta | `#e87ba4` | `#d55181` | Promo “Oferta Business Edition” |
| 6 green | `#008300` | `#008300` | reserved |
| 7 violet | `#6250d6` | `#9085e9` | Badge “Dodatkowe 15 000 zł korzyści” |
| 8 red | `#e34948` | `#e66767` | reserved |

Engine groups on a model page take slots 1–5 in the fixed order TFSI, TDI, TFSI quattro, TDI quattro, e-hybrid / e-tron; a model with more groups folds the rest into “Other”. Comparing many models at once uses emphasis: the chosen model in slot 1, the others in the muted grey, never 53 colours.

Sequential (magnitude, e.g. discount % heatmap by model × engine group): blue ramp `#cde2fb` → `#0d366b` (steps 100–700). Diverging (price change): blue ↔ red with grey midpoint `#f0efec` / `#383835`.

### 8.3 Chart rules (from the dataviz skill, enforced in code review)

- One y-axis per chart; two measures of different scale are two charts or an index to 100.
- Lines 2 px round-capped; markers ≥ 8 px with a 2 px surface ring; bars ≤ 24 px with 4 px rounded data-ends and 2 px surface gaps; area fills at ~10 % opacity; gridlines solid hairlines.
- Legend always shown for 2+ series; a single series has none; direct labels only on the endpoint or the extreme; axis ticks compact (120K).
- Text never wears a series colour; identity comes from a colour key beside the text.
- Crosshair tooltip on every line chart listing all series at the hovered date, value first; per-mark tooltips on bars; the same on keyboard focus; a table view exists for every chart (the configuration table or a “show data” toggle).
- Status colours only for status (freshness, run state, price direction with an arrow icon and a label), never for a series.
- Colour follows the entity: filtering models out never recolours the survivors.
- Run `node validate_palette.js "<hex list>" --mode light` and `--mode dark` in CI whenever `tokens.css` changes (script copied from the skill into `web/tools/`).

### 8.4 Type, layout and voice (from the frontend-design skill)

- One typeface: IBM Plex Sans, self-hosted woff2 with the latin-ext subset for Polish; weights 400, 500, 600. Scale 12 / 14 / 16 / 20 / 28 / 40 px, line height 1.45 for body. `tabular-nums` only in tables and axes; proportional figures for KPI values.
- Left-aligned, max content width 1440 px, 12-column grid, 8 px spacing scale, one border radius (6 px), no drop shadows, no gradients, no decorative icons.
- Structure encodes meaning: dividers group, chips classify, numbering appears only where there is a sequence. No all-caps eyebrows, no middle-dot meta strings, no arrows appended to links, no monospace for data labels.
- One memorable element: the model board on the Overview (53 tiles with sparklines in the site’s own order). Everything else stays quiet.
- Motion: one page-load reveal of the model board; otherwise only motion that answers an action (drawer opening, filter applied). Respect `prefers-reduced-motion`.
- Copy: sentence case, active verbs, buttons name the action (“Export CSV”), errors say what happened and what to do, empty states invite the next action. Site-native terms stay in Polish and are explained once in About.
- Brand: no Audi logo, wordmark, rings or AudiType font; model names and promo wording are plain text; no links to audi.pl; the source is named as plain text in About.

Before building the UI, the implementer writes a half-page design plan (palette, type roles, an ASCII wireframe of the Overview and Model pages, three principles), checks it against the tells listed in the frontend-design skill, and commits it as `docs/design-plan.md`.

## 9. Repository layout and navigation

Two repositories. The public one holds everything a reader or contributor needs (code, rules, docs, aggregate data) and a README whose first table tells a newcomer where to go for each task. The private one holds the scheduled job and the offer-level data. Locally the two are cloned side by side, because the Makefile expects the private checkout at `../audilitics-private`.

```text
audilitics/                        public, github.com/rlgdev/audilitics
  README.md                        purpose, live URL, notice, “Start here” table, the three commands that matter
  Makefile                         collect, rebuild, guard, test, web (one entry point for every task)
  docs/
    SPEC.md                        this document; the source of truth for scope
    data-source.md                 section 3: endpoints, field dictionary, discarded fields, slider and badge rules
    data-model.md                  section 5: schemas (JSON Schema files alongside), file layout, publication rules
    analytics.md                   section 6: trends, changes, score, plans
    design-system.md               section 8 plus the copied dataviz reference files and the validator
    design-plan.md                 the half-page plan written before the UI (8.4)
    runbook.md                     failed, blocked and suspect runs, guard failures, rules review, replay
    decisions/                     ADR-0001-static-hosting.md … ADR-0009-public-trends-edition.md, one page each
    CHANGELOG.md                   user-visible changes per release, rules versions
    BACKLOG.md                     owner decisions and open work
  rules/
    promo_rules.yaml  plans.yaml  scoring.yaml  models.yaml
  collector/
    pyproject.toml  config.yaml
    collector/                     fetch.py redact.py normalise.py rules.py diff.py analytics.py indexes.py public.py guard.py export_xlsx.py report.py cli.py
    tests/                         unit tests + fixtures/synthetic/ (generated offers, invented prices and dealers)
    schemas/                       offer, snapshot, snapshot-index, latest, trends, deals, changes, model (public) and private-deals, private-dealers
  data/                            the public tree of 5.3, written only by the collector job
  web/
    package.json  vite.config.ts  index.html
    src/
      app/                         routes per edition, providers, layout
      pages/                       Overview Model Deals Changes About; private/ Offers Dealers Car
      components/                  section 7.4
      charts/                      ECharts theme from tokens, TrendChart, RangeChart, PromoMixChart, Sparkline
      lib/                         data loading (fetch + cache, edition roots), formatting (pl-PL), url state, filters
      styles/                      tokens.css, base.css
    tools/validate_palette.js
    e2e/                           Playwright smoke tests and screenshots on synthetic data
  .github/
    workflows/deploy-pages.yml  ci.yml
    ISSUE_TEMPLATE/  PULL_REQUEST_TEMPLATE.md  CODEOWNERS

audilitics-private/                private, github.com/rlgdev/audilitics-private
  README.md                        what is here, how to run the private dashboard, link to the public repository
  data/                            the private tree of 5.3, written only by the collector job
  fixtures/2026-10-13/raw.json.gz  redacted real feed for the acceptance tests of 12.1
  .github/workflows/collect.yml  ci.yml
```

### 9.1 Navigation conventions

- README “Start here” table: I want to… → file or command (see the live dashboard, run the collector locally, run the private dashboard, add a promo rule, fix a failed run or a guard failure, change the score, add a page).
- Every `docs/*.md` starts with two lines: what it covers and the date it was last verified against the site or the code.
- Each section number of this specification is referenced in the matching doc and in the code (`# spec 6.3`) so a reader can move between the two.
- One ADR per decision in the table of section 1, five to ten lines each: context, decision, consequences.
- Pull request template has a checkbox “rules or schema changed → docs and fixture updated”.
- Issue labels used by automation (private repository): `collector-failure`, `collector-blocked`, `schema-change`, `rules-review`, `publication-guard`.
- Names: `snake_case` in Python, `camelCase` in TypeScript, ISO dates in file names, model slugs as in `rules/models.yaml` (`a3-sportback-tfsi-e`, `q5-sportback-e-hybrid`, `rs-q8`).

## 10. Build, deployment and GitHub Pages

Four workflows in two repositories: `collect.yml` (private) writes data and pushes the public tree, `deploy-pages.yml` (public) publishes the site whenever `main` changes, and a `ci.yml` in each repository guards pull requests. The public repository never runs the collector against the live site.

### 10.1 Workflows

| Workflow | Repository | Trigger | Permissions and secrets | Steps |
|---|---|---|---|---|
| `collect.yml` | private | `schedule: 17 5 * * 1`, `workflow_dispatch(force, date)` | `contents: write`, `issues: write`; secret `PUBLIC_REPO_TOKEN`: fine-grained token for `rlgdev/audilitics` only, permission Contents read and write | checkout the private repository; checkout `rlgdev/audilitics` at `COLLECTOR_REF` (repository variable, default `main`) into `app/`; Python 3.12 with pip cache; `pip install -e app/collector`; collect into `data/`; publication guard and identifier check; commit and push `data/` with `github-actions[bot]`; mirror `data/public/` onto a checkout of the public repository’s `data/` (deleting files that are gone) and push it with the token as `data: trends <date>`; upload the run report as a job artifact; create or update the issues of 4.3 |
| `ci.yml` | private | `pull_request`, `push` to `main` | read | acceptance tests of 12.1 against `fixtures/2026-10-13/` with the collector from the public repository; identifier check over `data/` |
| `deploy-pages.yml` | public | `push` to `main` touching `web/**` or `data/**`; `workflow_dispatch` | `pages: write`, `id-token: write` | checkout, Node 22, `npm ci`, `vite build` with `VITE_EDITION=public` and `--base=/audilitics/`, publication guard on `data/`, copy `data/` into `web/dist/data/`, `actions/upload-pages-artifact`, `actions/deploy-pages` |
| `ci.yml` | public | `pull_request`, `push` to `main` | read | `ruff`, `mypy`, `pytest` on the synthetic fixture, `tsc --noEmit`, `eslint`, `vitest`, Playwright smoke of the public build on synthetic data, `validate_palette.js` light and dark, publication guard on `data/` |

Pushes made with the fine-grained token trigger `deploy-pages.yml`, so the `workflow_run` trigger of release 1.0 is removed. Pages source is set to “GitHub Actions” in the public repository’s settings. The site URL is `https://rlgdev.github.io/audilitics/`; the Vite `base` and the router basename come from one environment variable so a custom domain is a one-line change.

### 10.2 Data on the site

- The public dashboard fetches `./data/...` from its own origin; no CORS, no external hosts.
- The site serves the public repository’s `data/` as it is: everything in it is public by construction and passes the guard on every deploy.
- Files are stored uncompressed; GitHub Pages applies gzip or brotli on transfer.
- `data/manifest.json` with the latest snapshot date and file hashes is written per run; the dashboard reads it first and busts its in-memory cache when the date changes.

### 10.3 Local development

| Task | Command |
|---|---|
| Install everything | `make setup` (Python venv + `npm ci`) |
| Run the collector against the synthetic fixture | `make collect FIXTURE=1` |
| Run the collector against the redacted real fixture | `make collect FIXTURE=real DATA=../audilitics-private/data` |
| Serve the public dashboard with local data | `make web` (Vite dev server, `VITE_EDITION=public`) |
| Serve the private dashboard | `make web EDITION=private DATA=../audilitics-private/data` (local only, never deployed) |
| Check a public tree | `make guard` |
| Run all checks | `make test` |
| Replay history after a rules change | `make rebuild DATA=../audilitics-private/data`; the next run or a `workflow_dispatch` pushes the rebuilt public tree |

### 10.4 Access

The public repository and the GitHub Pages site are public and hold code, rules, docs and aggregate data only. The private repository is visible to the owner only; it holds the redacted offers, exports, run reports, the job that writes them, and its Actions logs and artifacts. The private dashboard is a local build and is never deployed. The fine-grained token can write only the contents of the public repository.

### 10.5 Publication guard

`collector/collector/guard.py`, run as `make guard` or `python -m collector guard <dir>`, lists every finding and exits non-zero when a file in a public tree breaks any check below. It runs in every collector job before the commit and the push, in the public repository’s CI and before every Pages deploy.

| Check | Fails on |
|---|---|
| Identifiers | A string matching `\b[A-HJ-NPR-Z0-9]{17}\b` (VIN shape, case-sensitive), or a key named `vin`, `komisja`, `link`, `kod_audi`, `telefon`, `phone` or `offer_id`; `.gz` files are read decompressed and `.xlsx` files by cell text |
| Dealers | A key named `dealer`, `dealer_nr` or `dealers` |
| Links | Any `http://` or `https://` string pointing to `audi.pl` or one of its subdomains |
| Group size | A price, rate, discount or score statistic in a group with `priced` below 3; badge or slider counts in a group with `offers` below 3; any statistic without its `offers` or `priced` count |
| Layout | A file whose path is not in the public layout of 5.3 |

The identifier check (first row) also runs over all of the private repository’s `data/`, in every collector run and in its CI, because VINs are out of scope everywhere.

## 11. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | Overview interactive in under 2 s on a desktop connection: first load ≤ 350 kB of JavaScript (gzipped) plus `latest.json` and `trends.json`; model files load on demand; a 5,000-row offer table in the private build scrolls at 60 fps through virtualisation; a filter change re-renders in under 100 ms |
| Reliability | A run is idempotent (re-running a date overwrites that snapshot); every gate of 4.3 has a test; a failed run leaves both repositories untouched and the previous site online; the dashboard shows a warning when data is older than 9 days |
| Reproducibility | Every derived file, public and private, can be rebuilt from the redacted `raw/` with `make rebuild`; rule sets are versioned with `valid_from`; the redacted fixture of 13 Oct 2026 reproduces the counts in section 12 |
| Politeness to the source | At most 10 requests per run, 1 s apart, identifying User-Agent with the public repository URL, no images, no bundle download, immediate stop on 403 or 429, no retries beyond 4.2, never a workaround of a block (other address, other User-Agent); one run per 14 days |
| Legal | Collection relies on the text-and-data-mining exception for databases (art. 8a ustawy o ochronie baz danych): the feed is copied only to compute trends, and no machine-readable reservation exists (3.6). Only aggregates are published, so no substantial part of the database is made available to the public, and no information of the site is reproduced at offer level, in line with §8.2–8.3 of the audi.pl Regulamin. No identifiers, offer links, phone numbers, brand assets, images or bundle copies are collected. About states that the figures are aggregates, not offers, and that the project is not affiliated with Audi. A reservation found later, a written objection from Volkswagen Group Polska, or a block stops collection until the owner decides (runbook) |
| Privacy | No VIN or derivative of it, no dealer phone, nothing about buyers. Dealer names (businesses) stay in the private repository. Every public figure rests on at least 3 offers (5.5) |
| Security | One secret only: the fine-grained token in the private repository, scoped to the public repository’s contents; dependencies pinned with lockfiles and Dependabot; feed strings rendered as text only; `Content-Security-Policy` meta allowing self and data URIs only; the collector never downloads, executes or stores the site’s bundle |
| Accessibility | WCAG 2.2 AA contrast for text; full keyboard operation; tooltips on focus; legend plus table for every chart; `prefers-reduced-motion` and `forced-colors` respected; Lighthouse accessibility ≥ 95 |
| Browser support | Last two versions of Chrome, Edge, Firefox, Safari; 375 px minimum width |
| Maintainability | Python typed and linted (`ruff`, `mypy` on the collector package), TypeScript strict; one place per rule (YAML), one place per token (`tokens.css`), one routes module for both editions; docs updated in the same pull request as behaviour |
| Observability | Run report per snapshot, job artifact and GitHub issue on failure, all in the private repository; the About page shows rules version, bundle hash and last run duration |
| Localisation | Numbers and dates in `pl-PL`; UI labels English; all site-native terms kept verbatim with a glossary in About |

## 12. Acceptance criteria and test plan

Release 1.1 is accepted when every item below passes on the fixtures and on one live run.

### 12.1 Acceptance criteria

- Collector on the redacted 13 Oct 2026 fixture (private repository) yields 4,768 offers, 53 models, 38 dealers, 3,092 versions; badge counts 2,347 / 230 / 4,676 / 1,916 / 2,847 / 81 (best offer, Final Edition, Leasing 101%, insurance, Business Edition, +15 000 zł; Business Edition corrected per ADR-0006); slider counts summed over models 2,347 / 230 / 4,675 / 1,916 / 2,847 (best offer, Final Edition, Leasing 101%, insurance, Business Edition). The numbers of configurations and of public configurations are recorded in the fixture’s expected output.
- Plan codes on the fixture: every `e-tron` model gets `APL-2` or `APL-2-EV`; A3 Limousine code `8YM` gets `APL-3`; Q5 code `GU` gets `APL-3`; A3 Sportback code `8YY` gets `APL-1`.
- Redaction: no file in either repository’s `data/`, in any fixture or in any run report contains a VIN-shaped string or a key of 3.5; a unit test feeds items carrying all five fields and finds none of them in any output.
- Publication guard: passes on the real public tree; fails on each seeded violation (a VIN-shaped string, a `link` key, an audi.pl URL, a `dealer` key, a configuration with 2 priced offers, a statistic without its count, a file outside the public layout).
- A live run with `force=true` commits a snapshot, the private files of 5.3, the Excel export and a report to the private repository, pushes the public tree to the public repository, and the Pages site shows the new date within 10 minutes of the push.
- Replaying the same raw file twice leaves both data trees byte-identical.
- A simulated feed with 60 % of the previous count is stored as `suspect` in the private repository, opens one `collector-failure` issue, and is absent from `trends.json` and from the public tree; running again with a full feed closes nothing automatically but marks the new snapshot `ok`.
- Overview renders KPIs, the hot panel, two trend charts and the 53-tile model board from `latest.json` and `trends.json` only (verified in the network panel).
- Public build: the network panel shows no request outside the site’s own origin and none for a `private/` or `snapshots/*.json.gz` file; `#/offers`, `#/dealers` and `#/car/...` show the not-found state; no rendered page contains a link to audi.pl.
- Model page for Audi Q5 shows median and min–max band over at least two snapshots; hovering any date lists count, median, min and max in one tooltip; the like-for-like index starts at 100; the configuration table lists only configurations with at least 3 priced offers.
- Best deals: every published configuration’s `score_median` equals the median of its offers’ scores in `private/deals.json`; “top 3 per model” yields at most 3 rows per model; no configuration below the minimum group size appears; `hot=1` lists exactly the configurations with `hot: true`.
- Changes: a configuration whose median special fell between the last two snapshots appears under price drops with old, new, difference and %; a configuration with at least 3 offers before and none now appears under gone configurations; stock by model shows net added and removed.
- Private build on the fixture: `#/offers` lists 4,766 scored offers (special and catalog price present) with no VIN or link column; the Car page of any offer shows its configuration’s history from `private/models/<slug>.json`.
- Any filtered URL reloaded in a new tab restores the same filters, sort and run.
- CSV export of a filtered configuration table contains exactly the visible rows and columns, numbers unformatted.
- The Excel export in the private repository opens in Excel with zero formula errors and the same five sheets as the 13 Oct workbook, without VIN or link columns.
- Dark mode renders every chart with the dark token set; the palette validator passes light and dark.
- Lighthouse on Overview: performance ≥ 90, accessibility ≥ 95, best practices ≥ 95.
- Keyboard-only walkthrough: filters, model tile, hot card, configuration drawer, theme toggle, all reachable with a visible focus ring.
- README “Start here” table, runbook and ADRs exist; `make setup && make test` passes on a clean clone of the public repository without access to the private one.
- Hot deals: the Overview panel shows at most 8 cards, every card’s configuration meets a rule of 6.5 inside the last 31 days, “See all” opens `#/deals?hot=1` with the same configurations first, and with a single snapshot the panel shows its empty state.
- Model lifecycle: on the fixture followed by three simulated runs without Audi A8, A8 becomes `retired`, leaves the model board and the model filter, and stays reachable at `#/model/a8` and in trends; a simulated run with a new model `Audi Q9` adds it with slug `q9`, segment Q, and lists it under new models in Changes; a later run with A8 offers sets it `active` again.
- Public history: the guard and the identifier check pass on every commit of the public repository (`git rev-list --all`), so no commit ever held a raw feed, a bundle copy, an offer-level file or a VIN.

### 12.2 Test plan

| Level | Scope | Tooling |
|---|---|---|
| Unit (collector) | redaction, normalisation, every badge rule, plan code, configuration and version keys, canonical order, configuration diff lists, score components, like-for-like index, minimum group size | `pytest`, synthetic fixture and hand-made edge cases (null price, configuration with 2 offers, configuration present in only one snapshot, 2025 production year) |
| Acceptance (collector) | the counts of 12.1 on real data | `pytest` in the private repository against the redacted 13 Oct 2026 fixture |
| Contract | live feed shape against the pydantic schema; count sanity | runs inside every collector job; failure follows 4.3 |
| Guard | every check of 10.5 with seeded violations | `pytest`; the guard itself runs on `data/` in both CIs |
| Unit (web) | formatting, URL state, filter reducers, score display, edition routing | `vitest` |
| Component | each component of 7.4 with fixture data, light and dark | `vitest` + Testing Library, screenshot per component stored in the repo |
| End-to-end | all public routes render with synthetic data; filter → URL → reload; CSV export; drawer; keyboard path; no external requests | Playwright against `vite preview` of the public build in `ci.yml` |
| Visual | one screenshot per public page per theme committed, from synthetic data; diff reviewed in pull requests | Playwright screenshots |
| Palette | six checks of the dataviz validator for `tokens.css` | `validate_palette.js` in `ci.yml` |
| Export | workbook recalculates with no `#REF!`, `#NAME?` or `#VALUE!` cells | LibreOffice headless recalc in `pytest` (private repository) |

## 13. Delivery milestones

Release 1.0 delivered M1–M4 on 13 Oct 2026 (CHANGELOG). Release 1.1 adds M5; its gate includes the go-public steps of 16.5, and nothing is public before that gate passes.

| Milestone | Delivers | Gate |
|---|---|---|
| M1 Data foundation (1.0) | Repository skeleton, collector with fixture and schemas, rule files, `collect.yml`, first live snapshot committed, Excel export | Delivered |
| M2 Dashboard core (1.0) | Design plan, tokens, ECharts theme, Overview, Model page, car table, drawer, filter row with URL state, `deploy-pages.yml` | Delivered |
| M3 Analytics (1.0) | Changes, Best deals, Dealers, Car pages; score, flags, like-for-like index | Delivered |
| M4 Hardening (1.0) | Runbook, ADRs, issue automation, visual regression suite, accessibility pass, About page, CHANGELOG 1.0 | Delivered |
| M5 Public trends edition (1.1) | Everything in section 16: redaction at ingestion, configuration analytics, minimum group size, publication guard, public and private builds, two repositories and their workflows, synthetic and redacted fixtures, updated docs | All of 12.1 checked; guard green on the public tree and on the public history; Pages site live from the public repository after 16.5 |

Release 2 candidates, not scheduled: Slack or Teams digest of hot deals after each run, alert rules per model (median price below a threshold), weekly cadence.

## 14. Reusable assets from the 13 Oct 2026 collection

Most of the discovery work is done: the feed is mapped, the promo logic is extracted, a workbook already shows the information architecture, and two bundled skills supply the design rules. Each asset below has a destination in the repositories.

| Asset | Where it is now | Reused as |
|---|---|---|
| Workbook `Audi_gotowe_do_odbioru_2026-10-13.xlsx` (Summary, Top & Bottom 10, Models, Engines, Payment plans) | Delivered in an earlier conversation | Page structure of Overview, Deals, Model and About; column sets of the configuration and offer tables (7.3); template for the private Excel export |
| Endpoint map, query parameters, field dictionary (section 3) | This document | `docs/data-source.md`; pydantic schema; `collector/fetch.py` constants |
| Badge and slider rules transcribed from `main.20ab651335fb4daeebc8.js`: model lists, code prefixes, package types, footnote selection | Section 3.4, `rules/promo_rules.yaml` v1 | Unchanged; unit tests per rule |
| Footnote to plan mapping `APL-1`, `APL-2`, `APL-2-EV`, `APL-3` with fee, term, mileage | Section 6.4, `rules/plans.yaml` | Unchanged; About page text |
| Model directory with the site’s display order and segments (53 models) | `data/meta/models.json`, `data_models2.json` | `rules/models.yaml` overrides (segment, order); the model list itself is discovered on every run (4.6) |
| Dealer directory (38 dealers) | `data/meta/dealers.json` | Private repository only, names and cities; phone numbers are removed (16.4) |
| First live raw feed of 13 Oct 2026 | `data/raw/2026-10-13.json.gz`, `collector/tests/fixtures/2026-10-13/` of release 1.0 | Redacted (16.4) into the private repository’s `data/raw/` and `fixtures/2026-10-13/`; the release 1.0 copies are deleted |
| Observed quirks: numeric strings, empty `cena_vtp` on 2 cars, empty engine on RS 5, `text/html` content type, slider vs badge differences | Section 3 | Edge-case tests; normalisation rules |
| Dataviz skill: reference palette, mark specs, interaction rules, anti-patterns, `validate_palette.js` | Bundled skill `dataviz`, copied into `docs/design-system.md` and `web/tools/` | Unchanged (8.1–8.3) |
| Frontend-design skill: design-plan process, typographic rules, list of generic tells, copy rules | Bundled skill `frontend-design` | `docs/design-plan.md` checklist (8.4) |
| xlsx skill conventions: formulas not values, recalculation check, zero formula errors | Bundled skill `xlsx` | Export tests in 12.2 |
| Built-in browser recipe used for discovery (fetch the feed from the page context, read bundle rules on the live site) | `docs/runbook.md` | Section “Re-verifying rules after a bundle change”, reading the live bundle instead of an archived copy |

Not reusable on purpose: Audi images, logos and the AudiType fonts seen on the site (brand assets); the site’s Angular code and bundle (only its rules are transcribed into YAML; the bundle is not archived); every file of release 1.0 that holds VINs, offer links or phone numbers.

## 15. Decisions, open questions and glossary

The legal and visibility questions of rev 37 are decided below; three questions remain open, each with a default so work can go on.

### 15.1 Decisions and open questions

Decided in rev 38 (13 Oct 2026, by the owner; ADR-0009):

- Publication: public repository and public Pages site with aggregates only (trends, model statistics, configuration-level deal scores); offer tables and the Car page live in a private repository and are viewed locally.
- Identifiers: VINs, dealer stock numbers, offer links and dealer phone numbers are out of scope; nothing links to individual offers or to audi.pl.
- Legal basis: the text-and-data-mining exception for databases for collection; no offer-level publication, which keeps within §8.2–8.3 of the audi.pl Regulamin (section 11, Legal). Written consent from Volkswagen Group Polska is not needed for this scope; ask for it before anything is ever published at offer level.
- User-Agent contact: the public repository URL; no personal e-mail. Automation issues go to the owner through the private repository.
- Dealer phone numbers: not collected.

Decided in rev 39 (22 Oct 2026, by the owner):

- Cadence: weekly. The job still fires every Monday 05:17 UTC; the guard drops from 13 to 6 days (one snapshot every Monday) and the staleness warning from 16 to 9 days. Backlog item 4 stays open for the extra month-start run only.

Open (defaults apply until decided):

- Public name: “Audilitics” contains the Audi trade mark. For a non-commercial project with a non-affiliation notice the risk is low (default: keep). A neutral name removes it, and renaming is cheapest before the repository goes public (16.5).
- UI language: English labels with Polish site terms (default), or Polish throughout.
- Cadence anchor: first run on the next Monday after M5 (default), or a fixed calendar day; and whether an extra manual run is taken at month start when promos change.

### 15.2 Glossary

| Term | Meaning in this project |
|---|---|
| Cena katalogowa / catalog price | List price, PLN gross, `cena_katalogowa` |
| Cena specjalna / special price | Discounted stock price, PLN gross, `cena_vtp` |
| Najniższa cena z 30 dni | Lowest price in the 30 days before the reduction, `cena_historyczna` (consumer-law reference price) |
| Rata APL | Audi Perfect Lease monthly rate, PLN net, for businesses, `rata` |
| Plan code | Which footnote assumptions apply to the rate: `APL-1`, `APL-2`, `APL-2-EV`, `APL-3` |
| Promo slider | One of the five switches at the bottom of the site’s filter panel; collected as counts per model only |
| Badge | A label on an offer card; the source of per-offer promo flags (3.4) |
| Rocznik / model year | `rok_modelowy`; `rok_produkcji` is the production year |
| Komisja | Dealer stock number used in offer links; discarded at ingestion (3.5) |
| Stock cleaning | Feed flag `stock_cleaning=Tak` that feeds the best-offer and insurance rules |
| Snapshot | One collector run: every offer observed on one date |
| Offer | One redacted item of one snapshot; it has no identity across runs (5.5) |
| Configuration | Model + engine + model code + model year; the unit compared across runs and the unit of publication |
| Version | Offers with identical configuration, prices, rate and badges (private) |
| Minimum group size | Every public figure rests on at least 3 priced offers of that snapshot (5.5) |
| Public / private build | The two editions of the dashboard: public on GitHub Pages, private on the owner’s machine (section 7) |
| Publication guard | The check that keeps identifiers, links, dealers, unknown files and small groups out of the public tree (10.5) |
| Like-for-like index | Price index built only from configurations with at least 3 priced offers in two consecutive snapshots |
| Deal score | 0–100 ranking of offers defined in 6.3; published per configuration as best and median score |
| Net added / removed | Sum of the positive / negative changes in configuration counts between two runs; a lower bound of turnover |
| Hot deal | Configuration in stock whose median price improved inside the last 31 days per 6.5; shown on the main screen |
| Retired model | Model with no offers in three consecutive runs; hidden by default, history kept, reactivated automatically when offers return |

Sources: gotowedoodbioru.audi.pl (feed, footnotes and bundle read on 13 Oct 2026); Regulamin of audi.pl, §8.2–8.3 (read 13 Oct 2026); ustawa o ochronie baz danych, art. 7, 8 and 8a (Dz.U. 2024 poz. 1769); CJEU C-319/22 on VINs as personal data; the `dataviz`, `frontend-design` and `xlsx` skills bundled with Claude; workbook `Audi_gotowe_do_odbioru_2026-10-13.xlsx`.

## 16. Changes from release 1.0

Release 1.0 (13 Oct 2026) collects VINs and offer links, publishes offer-level tables and runs in one repository. This section lists everything the implementer changes for release 1.1, in order; each item names the section that defines the target. All of it lands before anything is made public.

### 16.1 Collector

1. Add `redact.py`: drop the fields of 3.5 right after schema validation; remove `vin`, `komisja`, `link` and `phone` from `normalise.py`, the schemas, the exports and every writer; the offer type has no attribute for them (3.5, 4.2).
1. Slider pulls: count items per model and keep only the counts; stop setting slider bits in `promo_bits`; remove the slider VIN lists from the raw archive (3.4, 5.2).
1. Stop downloading the bundle: record the hash only; remove `data/raw/bundles/` and the unbudgeted request (3.1, 4.2).
1. Canonical order and `offer_id` (5.5). Remove `vehicles/history.json`, per-car `first_seen`, `last_seen` and `status`, `price_change`, `rate_change`, the `long_listed` and `biggest_drop_this_run` offer flags, dealer moves and the VIN-based like-for-like index.
1. Configuration analytics: like-for-like over matched configurations, `net_added` and `net_removed`, configuration changes, configuration momentum in the score, configuration score summary and rankings, hot deals by configuration (6.1–6.5).
1. Minimum group size `public_min_group: 3` wherever a public figure is written (5.5).
1. Split the outputs: `--data-dir` for the private tree with `data/private/` and `data/public/`; `public.py` writes the public tree; `guard.py` implements 10.5; the identifier check runs over all of `data/` (4.2, 4.3).
1. User-Agent with the public repository URL; remove the `contact` setting (4.2).
1. Excel export and `latest.csv`: private only, without VIN, link and phone columns.

### 16.2 Dashboard

1. `VITE_EDITION` with one routes module: public routes Overview, Model, Deals, Changes, About; the private build adds Offers, Dealers and Car (7.1, 7.5).
1. Public pages use the configuration table; the offer table, the Car page and Dealers move to the private build (7.3).
1. Remove every link to audi.pl and the offer-link column; About names the source as plain text (7.1, 7.5).
1. Dealer filter in the private build only; configuration semantics of the promo filter (7.2).
1. `HotConfigCard` and the hot panel on `hot_configs` (7.4, 7.6); Changes with a run picker instead of a pair picker; delete the in-browser diff (`web/src/lib/diff.ts`).
1. Regenerate the e2e screenshots from synthetic data; delete the `car-*` and `dealers-*` screenshots.

### 16.3 Repositories and workflows

1. Create the private repository `rlgdev/audilitics-private` with the layout of section 9 and the `collect.yml` and `ci.yml` of 10.1.
1. In the public repository: remove `collect.yml`; remove the `workflow_run` trigger from `deploy-pages.yml`; build with `VITE_EDITION=public`; run the guard before the deploy; add the guard to `ci.yml`.
1. After the new public repository exists (16.5 step 3), create the fine-grained token (repository `rlgdev/audilitics` only, Contents read and write) and store it as `PUBLIC_REPO_TOKEN` in the private repository; set the repository variable `COLLECTOR_REF` if the collector should run from a tag.
1. Makefile: `DATA`, `EDITION`, `FIXTURE=real` and `guard` (4.4, 10.3).

### 16.4 Data migration

1. Redact `data/raw/2026-10-13.json.gz`: first turn each slider VIN list into counts per model through the main feed (VINs absent from the main pull count under `null`), then drop the fields of 3.5, the VIN lists and the bundle entry; write the result to the private repository as `data/raw/2026-10-13.json.gz` and `fixtures/2026-10-13/raw.json.gz`.
1. Run `make rebuild` in the private repository to regenerate `snapshots/`, `private/`, `public/`, the exports and the report; remove phone numbers from `meta/dealers.json`.
1. Delete from the codebase: `data/raw/`, `data/snapshots/*.json.gz`, `data/vehicles/`, `data/exports/`, `data/reports/`, `data/dashboard/dealers.json`, the release 1.0 `data/dashboard/` and `data/models/` files, `collector/tests/fixtures/2026-10-13/`, and any JSON from the workbook that holds VINs. The public `data/` is then written only by the first 1.1 run.
1. Generate `collector/tests/fixtures/synthetic/`: about 300 offers over 6 models and 3 snapshots, invented prices and dealer names, including configurations below the minimum group size, with expected outputs.

### 16.5 Going public

The repository `rlgdev/audilitics` of release 1.0 holds the raw feed with VINs, the Audi bundle and offer-level files in its first commit, and its Actions artifacts hold run reports. It is never switched to public, not even after those files are deleted, because old commits stay reachable by their hash.

1. Rename `rlgdev/audilitics` to `rlgdev/audilitics-1.0` and keep it private. Delete it once release 1.1 has run successfully, since it holds VINs.
1. Create `rlgdev/audilitics-private` (private) as in 16.3 and push the migrated data of 16.4.
1. Create a new `rlgdev/audilitics`, private for now, and push the release 1.1 tree as one fresh commit, with no history from release 1.0.
1. Create the fine-grained token for the new `rlgdev/audilitics` (a token made before step 1 stays bound to the renamed repository) and add it to the private repository as `PUBLIC_REPO_TOKEN`.
1. Run `collect` once with `force: true` and read the run report; then run `make guard` and the public-history check of 12.1 on `rlgdev/audilitics`.
1. Only then switch `rlgdev/audilitics` to public, set Settings → Pages → Source to “GitHub Actions” and Settings → Actions → General → Workflow permissions to read (no workflow in the public repository writes), run `deploy-pages` and check the site.

Local clones: the existing folder becomes the 1.0 archive; clone `audilitics` and `audilitics-private` side by side (section 9).

### 16.6 Documentation

Update in the same pull request: README (notice: aggregates only, no links to audi.pl; “Going live” replaced by 16.5; “Start here” gains the private dashboard), `docs/data-source.md` (3.5), `docs/data-model.md` (section 5), `docs/analytics.md` (section 6), `docs/runbook.md` (rules review on the live bundle, guard failures, reservation check, block procedure), `docs/design-plan.md` (public wireframe without Dealers and car table), `docs/CHANGELOG.md` (1.1.0) and `docs/BACKLOG.md`. ADR-0009 is already in `docs/decisions/`.
