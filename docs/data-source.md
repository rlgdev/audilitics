Covers: the gotowedoodbioru.audi.pl JSON feed: endpoints, request budget, query parameters, field dictionary, fields discarded at ingestion, slider and badge rules, behaviour, the reservation check and the observed facts of 13 Oct 2026 (spec 3).
Last verified against the code: 2026-10-13.

# Data source

The site is an Angular app. It loads its whole stock from a few unauthenticated JSON endpoints under `/ajax/` of gotowedoodbioru.audi.pl. One request with a large page size returns every car (spec 3).

Code: `collector/collector/fetch.py` (requests, steps 1–6 of spec 4.2), `collector/collector/schema.py` (validation), `collector/collector/redact.py` (discarded fields). The base URL, page size, request budget, spacing, timeout, back-off, User-Agent and `discarded_fields` live in `collector/config.yaml` (spec 4.5).

## Endpoints (spec 3.1)

Paths are relative to the site’s base URL (`base_url` in `collector/config.yaml`).

| Endpoint | Returns | Collector use |
|---|---|---|
| `GET /` | Index HTML | Read the bundle name `main.<hash>.js` (regex `main\.([0-9a-f]+)\.js`); record name and hash |
| `GET /ajax/data_models2.json` | Per model: `count, engine[], business_edition, moj_elektryk, rp[], stock_cleaning[], perfect_financing` | Model discovery (spec 4.6); its key order is the site order of models |
| `GET /ajax/data_dealers2.json` | `{dealer_nr: dealer name}` | Dealer directory, private repository only |
| `GET /ajax/get2.php?p=1&c=20000&s=price&d=asc` | `{count, items[]}`, every car | The main pull, once per run; items are redacted right after validation (spec 3.5) |
| `GET /ajax/get2.php?…&<slider params>` | Same shape, filtered | One call per slider; only the number of items per model is kept, in memory |
| `GET /ajax/get-filtered.php?<filters>` | `{model_counts: {model: n}}` | Not called (request budget, ADR-0005) |
| `GET /ajax/image.php?…` | Car image | Never fetched |
| `GET /main.<hash>.js` | App bundle; badge and footnote rules live here | Never requested, downloaded or archived. Only the hash is recorded; a new hash raises a `rules-review` issue |

The feed answers with `Content-Type: text/html` although the body is JSON. The collector decodes the body as UTF-8 (BOM tolerated) and parses it as JSON regardless of the content type.

## Request budget (spec 2, 4.2, 11)

`request_budget: 10` in `collector/config.yaml`. A run makes exactly 10 budgeted requests:

| # | Request |
|---|---|
| 1 | `GET /` |
| 2 | `GET /ajax/data_models2.json` |
| 3 | `GET /ajax/data_dealers2.json` |
| 4 | Main pull `get2.php` |
| 5–10 | Six slider pulls: `bo`, `fe`, `l101`, `pu`, `be`, `pks` |

Retries of the main pull (spec 4.2 step 3, back-off 10 s, 30 s, 90 s) are not counted again. Requests are spaced `request_spacing_s: 1.0` apart. A request beyond the budget fails the run. HTTP 403 or 429 stops the run at once with no retry. The run report lists every request with a "Budgeted" column.

Every request carries `User-Agent: audilitics/1.1.0 (price trend research; +https://github.com/rlgdev/audilitics)`, built from `user_agent`, the collector version and `public_repo` in `collector/config.yaml`. There is no personal e-mail in it (spec 15.1).

## Query parameters of `get2.php` (spec 3.2)

| Parameter | Meaning | Values seen |
|---|---|---|
| `p`, `c` | Page, page size | Site uses `c=12`; `c=20000` returns all |
| `s`, `d` | Sort field and direction | `price`, `asc` or `desc` |
| `m[]` | Model name filter (repeatable) | `Audi Q7` |
| `mc[]` | Model-code prefix filter with wildcard | `4MQ*` |
| `e[]` | Engine group filter | values of `silnik2` |
| `a_nr[]` | Dealer number filter | `0090` |
| `bo` | Slider "Najlepsza oferta z rocznika 2026" | `Tak` |
| `l101badge` | Slider "Leasing 101%" | `Tak` |
| `pu` | Slider "Pakiet ubezpieczeń za 1 zł" | `Tak` |
| `b` | Slider "Oferta Business Edition" | `Tak` |
| `rm` | Model-year filter, used by the Q7 Final Edition slider with `m[]` and `mc[]` | `2026` |
| `pks`, `l101`, `pf`, `me` | Service package, legacy leasing flag, perfect financing, "Mój elektryk" | No slider today; the collector pulls `pks=Tak` anyway |

Sliders combine as AND. The site opens with `bo=Tak` switched on, which hides about half of the stock. The collector always pulls with no filters first.

## Field dictionary (spec 3.3)

All fields arrive as strings; an empty string means null. On a live run every item must carry every known field, the five discarded ones included; a missing known field fails the run (spec 4.3). A replay of an archived raw file checks only the kept fields, because the file is already redacted.

| Field | Meaning | Offer field | Observed 13 Oct 2026 |
|---|---|---|---|
| `vin` | Vehicle identification number | dropped (3.5) | unique per item |
| `model` | Model name as shown on the tile | `model` | 53 distinct |
| `silnik` | Engine line on the card | `engine` | empty for RS 5 (23 cars) |
| `silnik2` | Engine group used by the engine filter | `engine_group` | 14 values incl. `modele S`, `modele RS`, empty |
| `komisja` | Dealer stock (commission) number | dropped (3.5) | 10 digits |
| `kod_audi` | Unused | dropped (3.5) | always empty |
| `dealer`, `dealer_nr` | Dealer name and number | `dealer`, `dealer_nr` (private repository only) | 38 dealers; `90006` = "Dostępny na terenie całego kraju" |
| `telefon` | Dealer phone | dropped (3.5) | one per dealer |
| `cena_katalogowa` | Catalog price, PLN gross | `catalog` | 136,700 – 1,158,240 |
| `cena_vtp` | Special price ("cena specjalna"), PLN gross | `special` | empty for 2 cars |
| `cena_historyczna` | Lowest price in the 30 days before the reduction | `price_30d` | always present |
| `cena_historyczna_katalogowa` | Catalog price 30 days before | `catalog_30d` | differs from `cena_historyczna` for 2,580 cars |
| `rata` | Audi Perfect Lease monthly rate, PLN net, for businesses | `rate` | empty for the same 2 cars |
| `stara_rata` | Previous rate | `rate_old` | empty for 2,619 cars |
| `rata_historyczna` | Lowest rate in the 30 days before | `rate_30d` | |
| `rok_produkcji` | Production year | `production_year` | 2026 (4,766), 2025 (2) |
| `rok_modelowy` | Model year ("rocznik") | `model_year` | 2025 (899), 2026 (2,378), 2027 (1,491) |
| `kod_modelowy` | 6-character model code, drives most badge rules | `code` | e.g. `8YFBNG`, `4MQCN2` |
| `id` | `rok_modelowy + rok_produkcji + kod_modelowy`, not unique | not stored on the offer | |
| `business_edition` | `Tak` or `Nie` | `business_edition` (bool) | 2,847 Tak |
| `stock_cleaning` | Clearance flag; feeds the best-offer and insurance rules | `stock_cleaning` (bool) | 1,911 Tak |
| `moj_elektryk` | Subsidy programme flag | `moj_elektryk` (bool) | always Nie |
| `link` | Offer page on the source site | dropped (3.5) | one per item |

The redacted item is archived in `data/raw/<date>.json.gz` and the typed offer in `data/snapshots/<date>.json.gz`, both in the private repository (see `docs/data-model.md`).

## Fields discarded at ingestion (spec 3.5)

| Field | Why it is dropped |
|---|---|
| `vin` | Identifies one vehicle and can become personal data once the car is registered to a person; trends do not need it |
| `komisja` | Dealer stock number; with `dealer_nr` it addresses a single offer |
| `link` | Direct link to a single offer on the source site |
| `kod_audi` | Always empty; dropped to keep the stored schema minimal |
| `telefon` | Dealer phone number; not needed |

How it is enforced:

| Step | Where |
|---|---|
| Every item is checked for every known field, the five above included | `check_fields()` in `schema.py` |
| The five fields are removed from every item before anything is written, logged or normalised. No hash, prefix or other derivative is kept | `redact_items()` in `redact.py`, called by `validate_and_redact()` in `schema.py` |
| Only redacted items reach the pydantic model; `FeedItem` and the offer have no attribute for a dropped field | `FeedItem` in `schema.py`, `normalise.py` |
| An unknown field whose name looks identifying (`vin`, `link`, `url`, `href`, `phone`, `telefon`, `komisja`, `email`, `mail`, `nr_rej`, `rejestr`) or whose value holds a VIN-shaped string or an `http(s)://` URL is dropped too; only its name is reported (`schema-change` issue). Other unknown fields are kept in `extra` | `looks_identifying()` in `redact.py` |
| Slider responses are reduced to item counts per `model` in memory; their items are never stored | `count_by_model()` in `fetch.py` |
| A unit test feeds items with all five fields and asserts that no output contains them | `collector/tests/test_redact.py` |
| The identifier check of spec 10.5 fails a run on any VIN-shaped string or discarded key anywhere in the private repository’s `data/` | `identifier_check()` in `guard.py` |

The field list is `discarded_fields` in `collector/config.yaml`. Without an identifier an offer cannot be followed from one run to the next; everything that compares runs works on configurations (spec 5.1, 5.5).

## Promo sliders and card badges (spec 3.4)

The source of truth for the rules is `rules/promo_rules.yaml` (sliders, badges, model lists, footnote texts) and `rules/plans.yaml` (rate footnote and plan code). They were transcribed by hand from the bundle `main.20ab651335fb4daeebc8.js` on 13 Oct 2026 and are never parsed from the bundle automatically (spec 3.6). Each rule set has a `valid_from` date; a snapshot uses the newest set with `valid_from` on or before its date (`collector/collector/rules.py`).

Per-offer promo flags come from the badge rules only, because joining a slider response to the main pull would need an identifier. Slider responses are kept as counts per model: they show the site’s own filter numbers in the trends and cross-check the badge rules (quality gate of spec 4.3).

| Key | Promo (site wording) | Slider request | Card badge rule (rules v1) | Badge bit |
|---|---|---|---|---|
| `bo` | Najlepsza oferta z rocznika 2026 | `bo=Tak` | Code not starting with `8YFRWY`, `8YMRWY`, `8YV`, `8YY`, `8YW`, and (`stock_cleaning=Tak` or code starts with `8YF`, `8YM`, `8YJ`, `4MQ`) | 5 |
| `fe` | Audi Q7 Final Edition | `m[]=Audi Q7&m[]=Audi Q7 TFSI e&m[]=Audi SQ7&mc[]=4MQ*&rm=2026` | Model in that trio, code starts with `4MQ`, `rok_produkcji=2026` | 10 |
| `l101` | Leasing 101% | `l101badge=Tak` | `rok_produkcji=2025` and model in the Q5 family, or `rok_produkcji=2026` and model in the 53-name list | 7 |
| `pu` | Pakiet ubezpieczeń za 1 zł | `pu=Tak` | A package type other than none, first match wins: insuranceAndService = Q5 family and 2025; insuranceOrService = Q5 family, `stock_cleaning=Tak`, 2026; insuranceOrService = A6 Limousine / Avant incl. e-hybrid, code `FN2` or `FN5`, 2026; insuranceOnly = Q7 trio, `4MQ`, 2026 | 8 |
| `be` | Oferta Business Edition | `b=Tak` | `business_edition=Tak` and not Final Edition (the card shows the Final Edition badge instead) | 9 |
| `p15` | Dodatkowe 15 000 zł korzyści | none | A6 e-tron family with code `GH` or Q6 e-tron family with code `GF`, `rok_produkcji=2026` | 6 |
| `pks` | Service package | `pks=Tak` | no badge; slider count only | none |

Years in the badge rules are production years (`rok_produkcji`). The package type is stored on each offer as `package_type`. Slider bits 0–4 and 11 of release 1.0 are no longer set on offers (spec 5.2).

The slider-versus-badge gate compares, per promo, the slider total with the badge total and warns above 1 % (`gates.slider_badge_tolerance: 0.01`). For `be` it compares the slider with the number of offers carrying `business_edition=Tak`, because the slider also returns Final Edition cars whose card shows only the Final Edition badge (`slider_gate()` in `pipeline.py`; ADR-0006, Release 1.1 (c)).

Q5 family = Audi Q5, Q5 e-hybrid, Q5 Sportback, Q5 Sportback e-hybrid, SQ5, SQ5 Sportback. The full 2026 Leasing 101% list and both e-tron family lists are in `rules/promo_rules.yaml`.

### Rate footnote and plan code

The footnote next to the monthly rate selects the plan assumptions (spec 3.4, 6.4). Rules are checked in order in `rules/plans.yaml`; the first match wins:

| Footnote | Condition |
|---|---|
| 2 | Model name contains `e-tron` |
| 3 | (name contains `Q5` and code starts `GU`) or (`Q7` and `4MQ`) or (A3 Limousine `8YM`, A3 Sportback `8YF`, A3 allstreet `8YJ`, S3 Limousine `8YM`, S3 Sportback `8YF`) or code starts `4MT`, `FJ`, `FU`, `FN`, `4N` |
| 1 | Everything else |

Footnote 1 maps to `APL-1`, footnote 3 to `APL-3`. Footnote 2 maps to `APL-2`, except `APL-2-EV` when the model year is 2026 or the code starts `GH` or `GF`. Plan parameters are in `docs/analytics.md`.

## Behaviour to expect (spec 3.6)

- No cookies, tokens or headers are required. The cookie banner is client-side only.
- Responses are not cached. Counts can change between two calls in the same run, so the main pull is the record and the slider counts are a cross-check only.
- The bundle name changes on every site deploy. A new hash raises a `rules-review` issue (spec 4.3); a person then reads the rules on the live site (`docs/runbook.md`). The bundle is never parsed automatically, downloaded or archived.
- HTTP 403 or 429 stops the run at once with no retry and no workaround (`collector-blocked`). Other non-200 answers fail the run (`collector-failure`); HTTP 5xx and network errors are retried only on the main pull.
- The main pull must satisfy `count == len(items)`; otherwise it is retried with the back-off and then fails the run.

### Reservation check

On 13 Oct 2026 the subdomain had no `robots.txt` and no text-and-data-mining reservation: no `/.well-known/tdmrep.json`, no `tdm-*` response headers, no robots meta tag. `www.audi.pl/robots.txt` disallowed only `/userinfo/`. The runbook repeats this check at every rules review ([runbook](runbook.md#reservation-check-spec-36)). A reservation found later stops collection until the owner decides (spec 11, Legal).

## Observed facts of 13 Oct 2026

Snapshot `2026-10-13`, status `ok`, source `live`, rules `promo:v1/plans:v1/scoring:v1`, bundle hash `20ab651335fb4daeebc8`, fetch duration 11.4 s, 10 budgeted requests. The run was made by release 1.0 and redacted afterwards with `collector/tools/redact_raw_1_0.py` (spec 16.4); the redacted file is the private repository’s `data/raw/2026-10-13.json.gz` and `fixtures/2026-10-13/raw.json.gz`.

| Measure | Value |
|---|---|
| Offers | 4,768 |
| Models | 53 |
| Dealers | 38 |
| Versions (`version_key`) | 3,092 |
| Configurations (`config_key`) | 191 |
| Published configurations (at least 3 priced offers) | 149 |
| Scored offers (special and catalog price present) | 4,766 |

Slider counts, summed over models:

| `bo` | `fe` | `l101` | `pu` | `be` | `pks` |
|---|---|---|---|---|---|
| 2,347 | 230 | 4,675 | 1,916 | 2,847 | 1,686 |

Card badges, computed from the rules:

| `bo` | `fe` | `l101` | `pu` | `be` | `p15` |
|---|---|---|---|---|---|
| 2,347 | 230 | 4,676 | 1,916 | 2,847 | 81 |

Leasing 101% has one more badge than slider items; the odd car is an RS e-tron GT performance. None of the 230 Final Edition cars has `business_edition=Tak`, so the Business Edition badge count equals the flag count, 2,847 (ADR-0006 (a)).

Plan codes:

| `APL-3` | `APL-1` | `APL-2-EV` | `APL-2` |
|---|---|---|---|
| 3,958 | 677 | 81 | 52 |

The main pull response was 3,231,720 bytes, larger than the ~2.0 MB in spec 3.1.

Sources: gotowedoodbioru.audi.pl (feed, footnotes and bundle `main.20ab651335fb4daeebc8.js` read on the live site on 13 Oct 2026; the bundle is not archived).
