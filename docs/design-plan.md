Covers: palette, type roles, wireframes and principles of the dashboard (spec 8.4), written before the UI.
Last verified against the code: 2026-10-13.

# Design plan

## Palette

Tokens from spec 8.1 in `web/src/styles/tokens.css`; categorical slots 1–8 from spec 8.2, validated with
`web/tools/validate_palette.js` (light: all checks pass, contrast WARN on aqua / yellow / magenta → every chart
has a table view and promo chips carry text; dark: all checks pass). Status colours (good, critical, warning)
appear only for price direction, run state and stale data, always with an arrow icon or a word.

## Type roles

IBM Plex Sans only (self-hosted, latin-ext). 40 px page KPI hero is not used: the KPI row uses 28 px / 600.
20 px section titles, 16 px body, 14 px table and secondary text, 12 px axis ticks and chips.
`tabular-nums` in tables and axes only.

## Wireframes: public build

The public build (`VITE_EDITION=public`) has five routes: Overview, Model, Best deals, Changes, About (spec 7.1).
There is no Dealers page, no offer table, no Car page and no Dealer filter, and no page links to the source site.

```text
Overview (#/)
+--------------------------------------------------------------------------------+
| Audilitics   Overview  Best deals  Changes  About                     [theme]   |
| Audi stock ready for pickup: price trends                                       |
| Data from 13 paź 2026. Next run 26 paź 2026. Last run ok.                       |
| [Period] [Segment] [Model] [Engine] [Promo] [Plan]  [Show retired (n)]          |
+--------------------------------------------------------------------------------+
| Offers in stock 4 768 (+12) | Models with offers 53 | Median discount 20,0 %    |
| Lowest monthly rate 646 zł (APL-3) | Configurations with a price drop 14         |
+--------------------------------------------------------------------------------+
| Hot deals of the last month  16 wrz – 13 paź 2026, by configuration  See all (n)|
| [config card][config card][config card][config card] ... up to 8                |
|   card: model, engine and model year, offers, median special price,             |
|         drop amount and % (or "Lowest price seen"), best score, promo chips     |
+--------------------------------------------------------------------------------+
| Offers in stock (line)              | Median special price (line)               |
+--------------------------------------------------------------------------------+
| Models  (one tile per active model, in the site's order)                        |
| [A3 Limousine 259 ▲3  from 115 840 zł ~~~ chips] [A3 Sportback ...] ...          |
+--------------------------------------------------------------------------------+
| What changed this run: offers added and removed (net, by configuration),       |
| configurations with a price drop; Open Changes                                  |
+--------------------------------------------------------------------------------+

Model (#/model/q5)
+--------------------------------------------------------------------------------+
| Overview                                                                        |
| Audi Q5                                                                         |
| Segment Q. 1 496 offers on 13 paź 2026, special prices 210 000 zł to           |
| 330 000 zł, rates from 1 990 zł (APL-3) net. Engine groups: TFSI, TDI quattro.  |
| [filter row without Segment and Model]                                          |
| Special price: median line + min–max band   | Like-for-like price index (=100)  |
| Median special price by engine group        | Promo mix: grouped bars per run   |
| Configurations in stock now: configuration table (at least 3 priced offers),   |
|   column chooser, Export CSV; a row opens the configuration drawer              |
+--------------------------------------------------------------------------------+

Best deals (#/deals)
+--------------------------------------------------------------------------------+
| Best deals                                                                      |
| [filter row]  Segment tabs: All  A  Q  S / RS  e-tron                           |
| [ ] Top 3 per model   [ ] Hot deals of the last month only                      |
| Configuration table: best and median score (breakdown popover of the median     |
| components), flags, promo chips with counts; a row opens the drawer             |
+--------------------------------------------------------------------------------+

Changes (#/changes)
+--------------------------------------------------------------------------------+
| Changes   Run [13 paź 2026 compared with 29 wrz 2026 v]                         |
| Summary tiles                                                                   |
| Tabs: New configurations | Gone configurations | Price drops | Price rises |      |
|       Stock by model | Promo changes                                            |
+--------------------------------------------------------------------------------+
```

About names the source as plain text, explains the plans, promos, score and minimum group size, lists what is not
collected, and carries the notice: aggregates, not offers within the meaning of the Civil Code, not affiliated with
Audi or Volkswagen Group Polska.

## Private build additions

The private build (`VITE_EDITION=private`, `make web EDITION=private DATA=../audilitics-private/data`) runs only on
the owner’s machine. It adds, on the same layout:

- Nav items Offers and Dealers, between Changes and About, and "private" next to the brand.
- A Dealer filter in the filter row.
- Offers (`#/offers`): the offer table with score, breakdown popover, flags and promo chips; no VIN or link column.
- Dealers (`#/dealers`): dealer × offers × median discount %, and offers per dealer over time.
- Model page: "In stock now" with tabs Configurations and Offers.
- Car (`#/car/:date/:n`): one offer on one date with its configuration’s median-price history; no link to the source.

## Three principles

1. The model board is the one memorable element; everything else is quiet chrome around numbers.
2. One question per chart, one y-axis, colour follows the entity (a promo or engine group keeps its slot on
   every page; many models = emphasis, never 53 colours).
3. Every number is reachable without hovering: tooltips enhance, the configuration table and "Show data"
   toggles carry the values.

## Checked against the generic tells

No gradients, drop shadows, glassmorphism, emoji, decorative icons, all-caps eyebrows, middle-dot meta strings
(the freshness line uses plain sentences), arrows appended to links, centred hero, or monospace data labels.
One radius (6 px), 8 px spacing scale, left-aligned 1440 px grid. Motion: one board reveal on first load,
disabled under `prefers-reduced-motion`; hover lift only on hot-deal cards.
