Covers: entities, the offer and the configuration, offer_id and canonical order, the private and public trees under data/ with their JSON shapes, the minimum group size, publication rules, the publication guard, the JSON Schema files and determinism (spec 5, 10.2, 10.5).
Last verified against the code: 2026-10-13.

# Data model and file layout

An offer is one redacted item of one snapshot and has no identity outside it. The configuration (model + engine + model code + model year) is the unit compared across runs and the unit of publication. Offer-level files live in the private repository; aggregate files are written to `data/public/` and mirrored onto `data/` of the public repository (spec 5).

Code: `collector/collector/normalise.py` (offers), `collector/collector/pipeline.py` (raw, snapshot, index, gates, exports, report, guard), `collector/collector/indexes.py` (private derived files), `collector/collector/public.py` (public tree), `collector/collector/guard.py` (publication guard and identifier check), `collector/collector/io.py` (deterministic writing).

## Entities (spec 5.1)

| Entity | Key | Holds | Where |
|---|---|---|---|
| Snapshot | `date` (ISO, one per run) | Status (`ok`, `suspect`), counts, bundle hash, rules version, duration | Private `snapshots/`; the public index lists its date and status |
| Offer | `offer_id` = `<date>/<n>` | The redacted, normalised item plus derived fields | Private only |
| Configuration | `config_key` | Label, model slug, engine group, plan code, per-snapshot statistics, score summary | Public on a date when it has at least 3 priced offers; private otherwise |
| Version | `version_key` | Identical offers (`identical` count) | Private only |
| Model | `slug` | Name, segment, order, status, lifecycle dates, engine groups, per-snapshot statistics | Public |
| Dealer | `dealer_nr` | Name and city; no phone | Private only |
| Rule set | `valid_from` | Promo, plan and scoring rules applied from that date | Public `rules/` |

### Keys

| Key | Definition |
|---|---|
| `config_key` | First 16 hex characters of sha1 over `model`, `engine`, `code`, `model_year` (joined with `\x1f`, null as empty). Computed exactly as in release 1.0 (ADR-0006) |
| `version_key` | First 16 hex characters of sha1 over `model`, `engine`, `code`, `model_year`, `catalog`, `special`, `price_30d`, `rate`, `promo_bits`. From 1.1 `promo_bits` holds badge bits only |
| `offer_id` | `<date>/<n>`, where `n` is the 1-based position in the canonical order below. The same car on two dates has two unrelated ids |
| Configuration label | `<model without "Audi "> <engine or "(engine not listed)">, <code>, <model_year>`, for example `Q5 TFSI 150(204) kW(KM) S tronic, GUBAZG, 2026` |

Canonical order (spec 5.5): `model`, `engine`, `code`, `model_year`, `special` (nulls last), `catalog`, `rate`, `dealer_nr`, `promo_bits`, then feed order (`_order_key()` in `normalise.py`). Missing text values sort as empty strings.

## Offer fields (spec 5.2)

Built by `normalise()` in `normalise.py`. Numeric strings become numbers (integers when whole, otherwise rounded to 2 decimals). Empty strings become null. `Tak`/`Nie` becomes a boolean. There is no field for `vin`, `komisja`, `link`, `kod_audi` or `telefon` (spec 3.5).

| Field | Type | Source or definition |
|---|---|---|
| `offer_id` | string | `<date>/<n>` |
| `model` | string | `model`, trimmed |
| `engine` | string or null | `silnik` |
| `engine_group` | string or null | `silnik2` |
| `code` | string or null | `kod_modelowy` |
| `model_year`, `production_year` | string or null | `rok_modelowy`, `rok_produkcji` |
| `dealer_nr`, `dealer` | string or null | `dealer_nr`, `dealer` |
| `catalog`, `special` | number or null | `cena_katalogowa`, `cena_vtp` |
| `price_30d`, `catalog_30d` | number or null | `cena_historyczna`, `cena_historyczna_katalogowa` |
| `rate`, `rate_old`, `rate_30d` | number or null | `rata`, `stara_rata`, `rata_historyczna` |
| `business_edition`, `stock_cleaning`, `moj_elektryk` | boolean | `Tak` = true |
| `promo_bits` | integer | Badge bits, table below |
| `package_type` | string | Insurance badge package: `none`, `insuranceAndService`, `insuranceOrService`, `insuranceOnly` |
| `footnote` | integer | Rate footnote 1, 2 or 3 (`rules/plans.yaml`) |
| `plan_code` | string | `APL-1`, `APL-2`, `APL-2-EV` or `APL-3` |
| `discount` | number or null | `catalog - special`; null when either is null |
| `discount_pct` | number or null | `discount / catalog`, 4 decimals |
| `config_key`, `version_key` | string | Keys above |
| `extra` | object | Unknown, non-identifying feed fields; present only when the feed sends any |

`promo_bits` keeps the badge positions of release 1.0 (spec 5.2): 5 best offer (`bo`), 6 +15 000 zł (`p15`), 7 Leasing 101% (`l101`), 8 insurance (`pu`), 9 Business Edition (`be`), 10 Final Edition (`fe`). Slider bits 0–4 and 11 are no longer set, because slider membership would need an identifier. Positions are `badge_bit` in `rules/promo_rules.yaml`.

Fields that depend on other snapshots are not stored in snapshot files. They are computed by `indexes.py` on every rebuild and appear only in the private offer tables:

| Field | Definition |
|---|---|
| `config_change` | Median special price of the offer’s configuration minus the same median in the previous `ok` snapshot; null when the configuration is new there (no priced offer in the previous `ok` snapshot) or has no priced offer now |
| `lowest_ever` | `special` is not null and not above the lowest `special` seen for this `config_key` across all `ok` snapshots so far |
| `identical` | Offers of the current snapshot with the same `version_key` |
| `initial_fee`, `term` | Plan `fee_pct` × `catalog` (rounded) and plan months |
| `score`, `D`, `P`, `M`, `R`, `B` | Deal score and components (`docs/analytics.md`); null without a special price |
| `flags` | `lowest_ever`, `last_one` (only offer of its version) |
| `hot` | The offer’s configuration is a hot deal (spec 6.5) |

## Private tree (`rlgdev/audilitics-private`, spec 5.3)

```text
data/
  raw/<date>.json.gz              redacted feed items, slider counts per model, models and dealers JSON,
                                  selected headers, request log
  snapshots/<date>.json.gz        normalised offers of one date in canonical order
  snapshots/index.json            one entry per stored snapshot
  private/models/<slug>.json      per model: current offers and every configuration with its full history
  private/deals.json              scored current offers with the score breakdown; rankings by offer_id
  private/dealers.json            per dealer per snapshot: offers, median discount_pct, models now
  public/                         the public tree below, byte-identical to what is pushed
  meta/models.json, meta/dealers.json, meta/bundles.json
  exports/<date>.xlsx, exports/latest.csv
  reports/<date>.md               run report
fixtures/2026-10-13/raw.json.gz   redacted real feed for the acceptance tests of spec 12.1 (with expected.json)
```

`raw/` and `snapshots/` are the inputs. Everything else under `data/` is rebuilt from all `ok` snapshots on every run (ADR-0008). Each run also writes `.run/result.json` and `.run/report.md` next to `data/` (outside it) for the workflow; they are not committed.

### raw/&lt;date&gt;.json.gz

```json
{
  "date": "2026-10-13",
  "fetched_at": "<ISO timestamp, UTC>",
  "duration_s": 11.4,
  "collector_version": "1.1.0",
  "source": "live",
  "redacted": true,
  "bundle": {"name": "main.<hash>.js", "hash": "<hash>"},
  "models_json": {"<model>": {"count": 0, "engine": [], "...": "..."}},
  "dealers_json": {"<dealer_nr>": "<name>"},
  "feed": {"count": 4768, "items": [{"model": "...", "...": "redacted feed fields"}]},
  "schema": {"unknown_fields": [], "dropped_identifying_fields": []},
  "slider_counts": {"bo": {"<model>": 0}, "fe": {}, "l101": {}, "pu": {}, "be": {}, "pks": {}},
  "headers": {"Content-Type": "text/html; charset=UTF-8"},
  "requests": [{"path": "/", "params": [], "attempt": 1, "counted": true, "status": 200, "bytes": 22270,
                "ms": 469, "content_type": "text/html"}],
  "request_count": 10
}
```

`headers` keeps only `content-type`, `content-length`, `date`, `server`, `last-modified` and `cache-control` of the main pull. The migrated 13 Oct 2026 file also carries `"migrated_from": "1.0"`; its slider counts were derived from the release 1.0 VIN lists through the main feed, and items absent from the main pull would count under the model key `null` (none did). A replay re-validates the items and ignores the release 1.0 keys `sliders` and `_bundle_bytes`.

### snapshots/&lt;date&gt;.json.gz

```json
{
  "date": "2026-10-13",
  "status": "ok",
  "rules_version": "promo:v1/plans:v1/scoring:v1",
  "bundle_hash": "20ab651335fb4daeebc8",
  "models_listed": ["Audi A3 Limousine", "..."],
  "dealers_json": {"<dealer_nr>": "<name>"},
  "slider_counts": {"bo": {"<model>": 0}, "...": {}},
  "offers": [{"offer_id": "2026-10-13/1", "model": "...", "...": "offer fields"}]
}
```

`offers` is in canonical order. `models_listed` is the key order of `data_models2.json`, used as the site order of models.

### snapshots/index.json (private)

```json
[{"date": "2026-10-13", "status": "ok", "offers": 4768, "models": 53, "configurations": 191, "dealers": 38,
  "versions": 3092, "bundle_hash": "20ab651335fb4daeebc8", "rules_version": "promo:v1/plans:v1/scoring:v1",
  "duration_s": 11.4, "source": "live", "warnings": []}]
```

`status` is `ok` or `suspect`; a `failed` run writes no snapshot and no entry (spec 4.3). An entry may carry `"status_set_by": "maintainer"` after a maintainer has promoted a `suspect` snapshot to `ok`; that override survives replays and `make rebuild` (`docs/runbook.md`).

### private/models/&lt;slug&gt;.json

```json
{
  "model": {"name": "...", "slug": "...", "segment": "Q", "status": "active"},
  "dates": ["2026-10-13"],
  "offers": {"columns": ["offer_id", "..."], "rows": [["...", "..."]]},
  "configurations": [{"config_key": "...", "label": "...", "model": "...", "slug": "...", "segment": "Q",
                      "engine": "...", "engine_group": "...", "code": "...", "model_year": "...",
                      "plan_code": "APL-3",
                      "history": {"offers": [], "priced": [], "special_min": [], "special_median": [],
                                  "special_max": []}}]
}
```

The history arrays are aligned with `dates` and are not limited by the minimum group size. Files of models no longer in the directory are deleted.

### Offer tables: `columns` / `rows`

`private/deals.json` and `private/models/<slug>.json` store offers as a table: `columns` is a list of names, `rows` a list of arrays in the same order:

`offer_id, model, slug, segment, engine, engine_group, code, model_year, production_year, catalog, special, discount, discount_pct, price_30d, promo_bits, rate, plan_code, initial_fee, term, identical, dealer_nr, dealer, config_key, config_change, lowest_ever, score, D, P, M, R, B, flags, hot`

There is no VIN, link, stock number or phone column (`private-deals.schema.json` rejects them).

### private/deals.json

```json
{"date": "2026-10-13", "hot_window": ["2026-10-13", "2026-10-13"],
 "columns": ["offer_id", "..."], "rows": [["2026-10-13/1", "..."]],
 "rankings": {"top_overall": ["<offer_id>"], "top_per_model": {"<slug>": ["<offer_id>"]},
              "top_per_segment": {"A": ["<offer_id>"]}}}
```

Rows hold only scored offers (special and catalog price present), ordered by score, then larger `discount`, then `offer_id`. On 13 Oct 2026 that was 4,766 rows.

### private/dealers.json

```json
{"dates": ["2026-10-13"],
 "dealers": [{"nr": "0003", "name": "...", "city": "...", "offers": [12], "discount_pct_median": [0.19],
              "models_now": {"<slug>": 4}}]}
```

### meta/*.json (private)

| File | Shape |
|---|---|
| `meta/models.json` | List of model entries in display order: `name`, `slug`, `segment`, `order`, `status`, `first_seen`, `last_seen`, `retired_on`, `empty_runs`, `engine_groups`, `possible_rename_of`, `code_prefixes`, `cars_now`, `engine_slots` |
| `meta/dealers.json` | `{dealer_nr: {nr, name, city, first_seen, last_seen}}`, every dealer ever seen in any snapshot (including `suspect`); nothing is deleted; no phone |
| `meta/bundles.json` | `[{hash, first_seen}]` from the snapshot index; the bundle itself is never stored |

`city` is parsed from the dealer name where possible (text after ` - ` or `, `, or after a leading `Audi Centrum`, `Audi` or `Porsche`).

### Exports and reports (private)

| File | Content |
|---|---|
| `exports/<date>.xlsx` | Workbook of the run with the sheets Summary, Top & Bottom 10, Models, Engines, Payment plans; no VIN, link or phone column. Written only when the date is the newest `ok` snapshot |
| `exports/latest.csv` | Current offers, UTF-8 with BOM, the offer-table columns of spec 7.3 plus deal score and `offer_id` |
| `reports/<date>.md` | Counts (offers, models, configurations, published configurations, dealers, versions), quality gates, slider counts, warnings, model events, configuration changes summary, hot configurations, request log |

## Public tree (`data/` of `rlgdev/audilitics`, spec 5.3)

```text
data/
  manifest.json                   latest snapshot date and file hashes
  snapshots/index.json            ok runs with counts; suspect runs with date and status only
  dashboard/latest.json           everything the Overview needs
  dashboard/trends.json           totals, segments and models per snapshot
  dashboard/changes/<date>.json   configuration and model changes against the previous ok run
  dashboard/deals.json            every published configuration with its score summary and hot fields; rankings
  models/<slug>.json              per model: timeline, engine-group series, configurations with their history
  meta/models.json                model directory
```

These are the only paths the guard accepts. `write_public()` in `public.py` deletes files of earlier runs that are no longer part of the tree, and the job mirrors `data/public/` onto the public repository with deletions. Browser files are compact JSON, uncompressed; `manifest.json`, `snapshots/index.json` and `meta/models.json` are pretty-printed.

Every statistic object carries `offers` and `priced` next to its figures (rates: `priced` per plan), and in time series these counts are arrays aligned with `dates`, so the guard can check the minimum group size.

### manifest.json

```json
{"latest": "2026-10-13", "newest_snapshot": "2026-10-13",
 "files": {"dashboard/latest.json": "1df7937070a0", "...": "..."}}
```

`latest` is the newest `ok` date, `newest_snapshot` the newest snapshot of any status. `files` maps every other public file to the first 12 hex characters of its sha1. The dashboard reads the manifest first and uses the hash to bust its cache (spec 10.2).

### snapshots/index.json (public)

```json
[{"date": "2026-10-13", "status": "ok", "offers": 4768, "models": 53, "configurations": 191,
  "rules_version": "promo:v1/plans:v1/scoring:v1", "bundle_hash": "20ab651335fb4daeebc8"},
 {"date": "2026-10-27", "status": "suspect"}]
```

### dashboard/trends.json

```json
{"dates": ["2026-10-13"],
 "totals":   {"<series>": [], "config_drops": []},
 "segments": {"A": {"<series>": []}, "Q": {}, "S/RS": {}, "e-tron": {}},
 "models":   {"<slug>": {"<series>": [], "lowest_version_special": []}}}
```

Every array is aligned with `dates`. The series keys are `offers`, `priced`, `special_min`, `special_median`, `special_max`, `discount_pct_median`, `rates` (`{plan_code: {priced, rate_min, rate_median}}`), `promo_counts` (`{bo, fe, l101, pu, be, p15}`), `slider_counts` (`{bo, fe, l101, pu, be, pks}`), `net_added`, `net_removed` and `lfl_index`. Definitions are in `docs/analytics.md`.

### dashboard/latest.json

The only file the Overview needs (spec 5.3, 7.1).

| Key | Content |
|---|---|
| `run` | `date`, `status` (of the newest snapshot), `data_date` (newest `ok` date), `next_run`, `rules_version`, `bundle_hash`, `duration_s`, `snapshots_ok`, `collector_version`, `stale_after_days` |
| `kpis` | `offers` and `models` (`{value, delta, spark}`), `discount_pct_median` (`{discount_pct_median, priced}`), `rate_min` (`{rate_min, plan_code, model, priced}`, the lowest published rate of any model and plan), `config_drops` (`{value, first_run}`) |
| `models` | One tile per model in display order: `slug`, `name`, `segment`, `status`, `order`, `offers`, `delta`, `priced`, `special_min`, `spark` (`{special_median, priced}`, last 12 snapshots), `promos` (up to 3 badge keys), `engine_groups`, `first_seen`, `retired_on` |
| `hot_configs` | Up to 24 configurations in hot-score order: `config_key`, `label`, `model`, `slug`, `segment`, `engine`, `engine_group`, `code`, `model_year`, `plan_code`, `offers`, `priced`, `special_median`, `start_price`, `drop`, `drop_pct`, `score_best`, `hot_score`, `flags`, `reasons`, `promo_counts`, `points` (`[{date, special_median, priced}]`) |
| `hot_count`, `hot_window` | Number of hot configurations; `[start, end]` dates of the window |
| `changes` | `date`, `previous`, `summary`, `models_new`, `models_retired`, `models_returned` of the newest changes file |
| `directory` | `segments`, `engine_groups`, `plans`, `plan_footnotes`, `leasing_101`, `promos` (`name`, `slot`, `badge_bit`, `footnote`), `scoring` (weights, momentum cap, new-configuration momentum, bonuses, hot thresholds), `min_group`, `not_collected`. No dealers |

`next_run` is the first Monday on or after the newest snapshot date plus 13 days (spec 4.1).

### dashboard/deals.json

```json
{"date": "2026-10-13", "hot_window": ["2026-10-13", "2026-10-13"],
 "configs": [{"config_key": "...", "label": "...", "...": "configuration row"}],
 "rankings": {"top_overall": ["<config_key>"], "top_per_model": {"<slug>": ["<config_key>"]},
              "top_per_segment": {"A": ["<config_key>"]}}}
```

A configuration row holds `config_key`, `label`, `model`, `slug`, `segment`, `engine`, `engine_group`, `code`, `model_year`, `plan_code`, `offers`, `priced`, `catalog_median`, `special_min`, `special_median`, `special_max`, `price_30d_median`, `discount_pct_median`, `discount_pct_max`, `rate_min`, `term`, `initial_fee`, `score_best`, `score_median`, `components` (`{D, P, M, R, B}` medians), `offers_80`, `promo_counts`, `flags`, `hot`, `hot_score`, `drop`, `drop_pct`. Only configurations published on the current date appear (149 on 13 Oct 2026). Rows are in ranking order.

### models/&lt;slug&gt;.json

```json
{
  "model": {"name": "...", "slug": "...", "segment": "Q", "order": 1, "status": "active",
            "first_seen": "...", "last_seen": "...", "retired_on": null, "empty_runs": 0,
            "engine_groups": ["TFSI"], "engine_slots": {"TFSI": 1}, "possible_rename_of": null},
  "dates": ["2026-10-13"],
  "timeline": {"<series>": [], "lowest_version_special": []},
  "engines": {"<engine_group>": {"slot": 1, "offers": [], "priced": [], "special_min": [], "special_median": []}},
  "configurations": [{"config_key": "...", "label": "...", "...": "...", "current": {"...": "configuration row"},
                      "history": {"offers": [], "priced": [], "special_min": [], "special_median": [],
                                  "special_max": []}}]
}
```

`timeline` is the model’s series from `trends.json`. `configurations` lists every configuration of the model that was published at least once; `current` is its row in `deals.json` or null when it is not published now, and `history` is null on dates where it was not published.

### dashboard/changes/&lt;date&gt;.json

One file per `ok` snapshot. Keys: `date`, `previous`, `configs_new`, `configs_gone`, `price_drops`, `price_rises`, `stock`, `promo_changes`, `models_new`, `models_retired`, `models_returned`, `summary`. Entry fields are in `docs/analytics.md`. The first snapshot has empty lists and `summary.first_run: true`.

### meta/models.json (public)

List of model entries in display order: `name`, `slug`, `segment`, `order`, `status`, `first_seen`, `last_seen`, `retired_on`, `engine_groups`.

## Minimum group size and publication rules (spec 5.5)

`public_min_group: 3` in `collector/config.yaml`.

| Rule | Implementation |
|---|---|
| Every price, rate, discount or score figure rests on at least 3 priced offers of that snapshot | `stats()` in `analytics.py` returns null below the threshold; rates per plan need 3 priced offers with a rate in that plan |
| Badge and slider counts rest on at least 3 offers | `promo_counts` and `slider_counts` are null below 3 offers in the group |
| Counts of offers are always published | `offers` and `priced` of every group; a configuration below the threshold still counts in its model, segment and total |
| A configuration has a public row on a date only with at least 3 priced offers | `config_summary()` is computed only for those; `history` is null on other dates |
| No offer-level row, no `offer_id`, no dealer name or number, no URL to audi.pl, no field of spec 3.5, no score components of a single offer | `public.py` writes only aggregates; configuration `components` are medians |
| A `suspect` snapshot is excluded from every public figure | `indexes.py` reads only `ok` snapshots; the public index lists a suspect run with date and status only, so the dashboard can warn |
| Dates are the run date in UTC; the dashboards show them in Europe/Warsaw | `pipeline.py`, `web/src/lib/format.ts` |

## Publication guard (spec 10.5)

`guard_public()` in `collector/collector/guard.py`, run as `make guard` or `python -m collector guard <dir>`, lists every finding and exits non-zero. It runs in every collector job before the commit and the push, in the public repository’s `ci.yml` and before every Pages deploy.

| Check | Fails on |
|---|---|
| Identifiers | A string matching `\b[A-HJ-NPR-Z0-9]{17}\b` (VIN shape, case-sensitive), or a key named `vin`, `komisja`, `link`, `kod_audi`, `telefon`, `phone` or `offer_id` |
| Dealers | A key named `dealer`, `dealer_nr` or `dealers` |
| Links | An `http://` or `https://` string pointing to audi.pl or one of its subdomains |
| Group size | A price, rate, discount or score statistic (including `lfl_index`, `lowest_version_special`, `start_price`, `drop`, `drop_pct`, `hot_score` and the `old`, `new`, `diff`, `pct` of changes) in an object whose `priced` is below 3, element by element in time series; `promo_counts`, `slider_counts` or `promo_changes` in an object whose `offers` (and `offers_before`) is below 3; any such statistic without its count |
| Layout | A file whose path is not one of the public paths above |

`.gz` files are read decompressed and `.xlsx` files by cell text. The identifier check (`identifier_check()`, `python -m collector idcheck <dir> [--public]`) also runs over all of the private repository’s `data/` in every collector run and in its CI. Over the private tree it does not treat `offer_id` as an identifier, because private files must hold offer ids; with `--public` it does (ADR-0006, Release 1.1 (a)).

## JSON Schema files

JSON Schema files (draft 2020-12) for the stored shapes are in `collector/schemas/`. `collector/tests/test_schemas.py` validates real collector output on the synthetic fixture against them on every test run. The feed item schema enforced at run time is the pydantic model in `collector/collector/schema.py`.

| File | Describes |
|---|---|
| `offer.schema.json` | One offer of a snapshot (spec 5.2); no property for a field of spec 3.5 |
| `snapshot.schema.json` | Private `snapshots/<date>.json.gz` |
| `snapshot-index.schema.json` | `snapshots/index.json`, private (full entries) and public (ok: counts; suspect: date and status) |
| `latest.schema.json` | Public `dashboard/latest.json` |
| `trends.schema.json` | Public `dashboard/trends.json` |
| `deals.schema.json` | Public `dashboard/deals.json` |
| `changes.schema.json` | Public `dashboard/changes/<date>.json` |
| `model.schema.json` | Public `models/<slug>.json` |
| `private-deals.schema.json` | Private `private/deals.json`; rejects VIN, link, stock number and phone columns |
| `private-dealers.schema.json` | Private `private/dealers.json`; rejects a phone field |

## Determinism

Running the same date twice leaves both trees byte-identical (spec 12.1; `test_same_raw_twice_is_byte_identical`, `test_rebuild_reproduces`).

| Mechanism | Where |
|---|---|
| JSON written with fixed separators and key order from the code; lists sorted (dates, labels, dealers, canonical offer order) | `io.py`, `indexes.py`, `public.py` |
| A file is rewritten only when its bytes change | `io.write_text` |
| gzip with `mtime=0`, empty file name, level 9 | `io.write_json_gz` |
| Workbook `created` and `modified` set to `<date>T00:00:00`; zip entries dated 1980-01-01; `dcterms:created` and `dcterms:modified` rewritten to the run date | `export_xlsx.py` |
| Run report has no wall-clock values other than those archived in the raw file | `report.py` |
