Covers: group statistics and trends, the like-for-like index, net stock movement, configuration changes, the deal score and configuration summary, flags, rankings, hot deals and payment-plan assumptions as computed by the collector (spec 6).
Last verified against the code: 2026-10-13.

# Analytics

All figures are computed by the collector from `ok` snapshots: configuration, model, segment and total aggregates go to the public tree, offer-level scores to `data/private/`. The dashboards never recompute them. `suspect` snapshots are ignored everywhere (spec 4.3). No figure follows a single car across runs: runs are compared through configurations matched by `config_key` (spec 5.5).

Code: `collector/collector/analytics.py` (`stats`, `score_offers`, `config_summary`, `lfl_step`, `hot_configs`), `collector/collector/indexes.py` (walks the snapshots, flags, net movement, private files), `collector/collector/diff.py` (changes), `collector/collector/public.py` (public files). Parameters: `rules/scoring.yaml` and `rules/plans.yaml`, rule set v1, `valid_from: 2026-10-13`; scoring and plan parameters come from the rule set of the newest `ok` snapshot.

Offers without a special price stay in counts but are left out of price statistics, rate statistics and scoring (spec 6). Every public figure obeys the minimum group size of 3 (spec 5.5, `public_min_group` in `collector/config.yaml`).

## Statistics and trends (spec 6.1)

`stats()` computes one statistic object per group of offers. Groups: totals, the four segments (A, Q, S/RS, e-tron), each model, each engine group of a model, and each configuration. The public files carry one value per `ok` snapshot in arrays aligned with `dates`: `dashboard/trends.json` (totals, segments, models) and `models/<slug>.json` (`timeline` and `engines`).

| Measure | Definition per snapshot |
|---|---|
| `offers` | Offers in the group (0 when a model has none) |
| `priced` | Offers with a special price |
| `special_min`, `special_median`, `special_max` | Over `special`; null below 3 priced offers |
| `discount_pct_median` | Median `discount_pct` of priced offers, 4 decimals; null below 3 priced offers |
| `rates` | Per `plan_code`: `priced` (priced offers with a rate in that plan), `rate_min`, `rate_median`; null below 3 in that plan. A 24-month rate is never pooled with a 36-month rate |
| `promo_counts` | Offers per badge `bo`, `fe`, `l101`, `pu`, `be`, `p15` (badge bits); null below 3 offers |
| `slider_counts` | Items per slider request `bo`, `fe`, `l101`, `pu`, `be`, `pks`: the site’s own filter numbers, summed over the group’s models; totals, segments and models only; null below 3 offers |
| `net_added`, `net_removed` | Net stock movement, below; null on the first snapshot |
| `lfl_index` | Like-for-like index, below; null where the group has fewer than 3 priced offers |
| `lowest_version_special` | Lowest published `special_min` of the model across all `ok` snapshots so far; models only |
| `config_drops` | Configurations whose median special fell against the previous `ok` snapshot (both dates published); totals only; null on the first snapshot |

Engine-group series in `models/<slug>.json` carry `offers`, `priced`, `special_min` and `special_median` under the same rules, plus the group’s colour `slot` (spec 8.2). Configuration statistics add `discount_pct_max`, `catalog_median` and `price_30d_median`.

The Overview KPIs in `latest.json` are totals: offers with delta and a 12-point sparkline, models with offers, median discount %, the lowest published rate with its model and plan, and `config_drops`.

### Like-for-like index

For each pair of consecutive `ok` snapshots, `lfl_step()` takes every configuration of the group with at least 3 priced offers in both and computes the median of `special_median_t / special_median_t-1`. The index starts at 100 on the first `ok` snapshot and is multiplied by that median at each step. A step with no matched configuration keeps the index flat. Values are rounded to 2 decimals after chaining. The index exists for totals, each segment and each model; it shows price moves without mix effects.

### Net stock movement

For each configuration, the change in its number of offers against the previous `ok` snapshot (all offers, no minimum group). `net_added` of a model is the sum of the positive changes of its configurations, `net_removed` the sum of the negative changes as a positive number. Segments and totals sum their models. It is a lower bound of real turnover: a sold car replaced by an identical one is invisible.

## Changes between consecutive snapshots (spec 6.2)

One file per `ok` snapshot, `dashboard/changes/<date>.json`, comparing it with the previous `ok` snapshot. A configuration is published on a date when it has at least 3 priced offers. Configuration entries carry `config_key`, `label`, `model`, `slug`, `engine`, `engine_group`, `code`, `model_year`, `plan_code`, plus:

| List | Extra fields | Rule |
|---|---|---|
| `configs_new` | `offers`, `priced`, `special_median`, `score_best`, `reason` | Published now and not in the previous snapshot. `reason`: `new_in_stock` (no offers before) or `reached_minimum` |
| `configs_gone` | `offers` (now), `priced` and `special_median` (last published), `reason` | Published before and not now. `reason`: `none_left` or `below_minimum` |
| `price_drops` | `offers`, `priced`, `old`, `new`, `diff`, `pct`, `consecutive_drops` | Published in both, median special lower now; sorted by `pct` ascending (largest drop first) |
| `price_rises` | `offers`, `priced`, `old`, `new`, `diff`, `pct` | Published in both, median special higher now; sorted by `pct` descending |
| `stock` | `model`, `slug`, `offers_before`, `offers`, `net_added`, `net_removed` | Every model present in either snapshot |
| `promo_changes` | `model`, `slug`, `offers_before`, `offers`, `promo_changes` (`{badge: {before, now}}`) | Models whose badge counts changed, when both snapshots have published badge counts (at least 3 offers) |
| `models_new`, `models_retired`, `models_returned` | `model`, `slug`, `segment`, `cars_now`, `first_seen`, `last_seen`, `possible_rename_of` | Model lifecycle events of that date (spec 4.6) |

`diff` = new minus old and `pct` = `diff / old`, 4 decimals, so drops are negative. `priced` on a price change is the smaller priced count of the two dates. `consecutive_drops` counts the consecutive snapshots in which the configuration’s published median fell, this one included.

`summary` holds the count of each list, `median_drop_pct` (median drop size as a positive fraction), `priced`, `largest_drop` (`label`, `config_key`, `diff`, `pct`, `priced`), `models_most_added` (up to 5 models by `net_added`), `first_run`, and the counts of new, retired and returned models. The first snapshot has empty lists and `first_run: true`.

The Changes page has a run picker of `ok` snapshots and shows the chosen run against the run before it; there is no free choice of pairs and no diff in the browser.

## Deal score (spec 6.3)

`score_offers()` scores every offer of the current snapshot with a special price and a non-zero catalog price. Range 0–100. Percentiles are within the same model unless stated.

| Component | Weight | Definition |
|---|---|---|
| Discount depth `D` | 0.35 | Percentile rank of `discount_pct` within the model |
| Price position `P` | 0.25 | 100 minus the percentile rank of `special` within the same model and engine group (`silnik2`) |
| Momentum `M` | 0.20 | Fall of the configuration’s median special since the previous `ok` snapshot: `drop = (prev_median - median_now) / prev_median`, `M = 100 × min(max(drop, 0), 0.05) / 0.05`. `prev_median` counts only when the configuration had at least 3 priced offers there; a new configuration, or one with fewer than 3 priced offers before, scores 50 (`momentum_new_car`) |
| Rate value `R` | 0.10 | 100 minus the percentile rank of `rate / special` within the same model and `plan_code`, among offers with a rate. An offer without a rate scores 0 |
| Promo bonus `B` | up to 10 | Insurance badge +4; Final Edition or +15 000 zł badge +4; best-offer badge +2 (badge bits) |

`score = 0.35 D + 0.25 P + 0.20 M + 0.10 R + B`, rounded half up to an integer. Each component is rounded to 1 decimal first and the score is computed from those values, so the five components stored for every offer in `private/deals.json` reproduce its score exactly. All offers of a configuration share the same `M`.

Weights, the 5 % momentum cap, the new-configuration momentum and the bonuses live in `rules/scoring.yaml`.

### Percentile rank

```text
pct_rank(x, values) = 100 × (below + 0.5 × (equal - 1)) / (n - 1)
  below = number of values strictly less than x
  equal = number of values equal to x (x itself included)
  n     = number of values in the group
pct_rank = 50 when n <= 1 (a group of one)
```

The lowest value scores 0 and the highest 100. Ties take the mid rank: in `[1, 2, 2, 3]` both 2s score 50.

### Configuration summary (public)

`config_summary()` runs only for configurations published on the date (at least 3 priced offers). It holds the statistics above plus:

| Field | Definition |
|---|---|
| `score_best`, `score_median` | Highest and median score of the configuration’s offers |
| `components` | Medians of `D`, `P`, `M`, `R`, `B` over its offers; they do not add up to the median score |
| `offers_80` | Offers scoring 80 or more |
| `plan_code`, `term` | The configuration’s plan and its term in months |
| `rate_min` | Lowest published rate over its plans |
| `initial_fee` | Plan `fee_pct` × `catalog_median`, rounded |

No single offer’s components are published.

### Flags

| Flag | Level | Definition |
|---|---|---|
| `lowest_ever` | Configuration (public) | `special_min` now is not above the lowest `special_min` of every date on which the configuration was published |
| `biggest_drop_this_run` | Configuration (public) | Its median drop % against the previous snapshot (published on both dates) is the largest in its model; ties all get the flag |
| `new_config` | Configuration (public) | First `ok` snapshot in which it is published. Not set on the first `ok` snapshot ever, otherwise every configuration would be flagged on day one (ADR-0006, Release 1.1 (b)) |
| `lowest_ever` | Offer (private) | `special` is not above the lowest `special` seen for its `config_key` across all `ok` snapshots so far |
| `last_one` | Offer (private) | No other current offer has the same `version_key` |

### Rankings

Public, in `dashboard/deals.json` under `rankings`, by `config_key`: `top_overall` (50), `top_per_model` (3 per slug), `top_per_segment` (10 per segment A, Q, S/RS, e-tron). Order: `score_best` descending, then `score_median` descending, then larger `discount_pct_median`, then label.

Private, in `private/deals.json`, the same three rankings of offers by `offer_id`. Order: score descending, then larger `discount`, then `offer_id`.

## Hot deals of the last month (spec 6.5)

A hot deal is a configuration in stock today, with at least 3 priced offers, whose price got clearly better within the last 31 days. `hot_configs()` computes them.

| Rule | Implementation |
|---|---|
| Window | All `ok` snapshots dated at most 31 days (`hot_window_days`) before the current one, including it |
| Minimum history | With a single `ok` snapshot in total nothing qualifies, and the Overview panel shows its empty state |
| Candidates | Configurations published today, with a `score_best` |
| Price points | `(date, special_median, priced)` in every window snapshot where the configuration had at least 3 priced offers; the first point gives the start price |

A configuration qualifies when at least one reason holds:

| Reason | Condition |
|---|---|
| `drop` | `drop = start price - median special now` is positive, and `drop / start >= 0.03` (`hot_drop_pct`) or `drop >= 5000` PLN (`hot_drop_pln`) |
| `lowest_ever` | The configuration has the `lowest_ever` flag now and its median fell between two consecutive points inside the window |
| `new_high_score` | First published inside the window, not on the first `ok` snapshot ever, and `score_best >= 80` (`hot_new_score`) |

`hot_score = score_best + min(20, 4 × drop in percent)`, where drop in percent = 100 × drop / start price and 0 when the price did not fall; rounded to 1 decimal. Order: hot score descending, then drop amount descending, then label.

`latest.json.hot_configs` holds up to 24 configurations (`hot_latest_limit`); the Overview panel shows up to 8. Every configuration in `deals.json` carries `hot`, `hot_score`, `drop` and `drop_pct`, and the Deals page lists all configurations with `hot: true` under `?hot=1`, in hot-score order. In the private build the offers of hot configurations carry `hot: true`.

On the synthetic fixture (three runs, 15 Sep to 13 Oct 2026) the last run has 7 hot configurations; its changes list 2 new and 1 gone configuration, 6 price drops and 2 rises (`collector/tests/fixtures/synthetic/expected.json`).

## Payment-plan assumptions (spec 6.4)

The site shows one Audi Perfect Lease rate per car: net, for businesses, calculated from the catalog price. The footnote the site assigns selects the plan (`docs/data-source.md`, `rules/plans.yaml`).

| Plan code | Footnote | Initial fee (of catalog price) | Term | Mileage per year |
|---|---|---|---|---|
| `APL-1` | 1 | 10 % | 36 months | 15,000 km |
| `APL-2` | 2 | 10 % | 24 months | 15,000 km |
| `APL-2-EV` | 2, exception | 8 % | 24 months | 15,000 km; model year 2026 or code starting `GH` (A6 e-tron range) or `GF` (Q6 e-tron range) |
| `APL-3` | 3 | 10 % | 24 months | 15,000 km |

`initial_fee = fee_pct × catalog` is stored per offer (private) and `fee_pct × catalog_median` per configuration (public), with `term`. The `rate_total = rate × term` of spec 6.4 is not computed or shown in release 1.1. Leasing 101 % (25 % initial fee, 24 months, 20 % residual) is a promo flag, not a rate. The plans, their footnote texts and the Leasing 101 % parameters are published in `latest.json.directory` for the About page.

On 13 Oct 2026: `APL-3` 3,958 offers, `APL-1` 677, `APL-2-EV` 81, `APL-2` 52.
