Covers: the visual design system of the dashboard - tokens, categorical slots, sequential and diverging scales, chart rules, type, layout and voice, the copied dataviz reference files and the palette validator (spec 8).
Last verified against the code: 2026-10-13.

# Design system

The dashboard reuses the validated reference palette and chart rules of the `dataviz` skill unchanged, and the design process of the `frontend-design` skill (spec 8). Every colour, font and spacing value is defined once, in `web/src/styles/tokens.css`. Charts read the tokens at run time through `getComputedStyle` (`web/src/lib/theme.tsx`, used by `web/src/charts/theme.ts`), so the ECharts theme follows light and dark mode without a second copy of the values.

The half-page design plan written before the UI is `docs/design-plan.md` (spec 8.4). Both builds of release 1.1, public and private, use the same tokens, components and rules (spec 7).

## Reference files

The dataviz skill's reference files are copied into `docs/design-system/` so the rules travel with the repository (spec 8, spec 14):

| File | Content |
|---|---|
| `docs/design-system/anti-patterns.md` | Chart mistakes to avoid |
| `docs/design-system/choosing-a-form.md` | Which chart form for which question |
| `docs/design-system/color-formula.md` | How the categorical palette is built and checked |
| `docs/design-system/components.md` | Stat tiles, legends, tooltips and other chart components |
| `docs/design-system/interaction.md` | Crosshair, hover, focus and table-view rules |
| `docs/design-system/marks-and-anatomy.md` | Line, marker, bar and gridline specifications |
| `docs/design-system/palette.md` | The validated default palette |

## Tokens (spec 8.1)

| Role | Token | Light | Dark |
|---|---|---|---|
| Page plane | `--page` | `#f9f9f7` | `#0d0d0d` |
| Chart and card surface | `--surface` | `#fcfcfb` | `#1a1a19` |
| Primary ink | `--ink` | `#0b0b0b` | `#f0efec` |
| Secondary ink | `--ink-2` | `#52514e` | `#c3c2b7` |
| Muted (axis, labels) | `--muted` | `#898781` | `#898781` |
| Gridline (1 px solid) | `--grid` | `#e1e0d9` | `#2c2c2a` |
| Baseline / axis | `--axis` | `#c3c2b7` | `#383835` |
| Border ring | `--ring` | `rgba(11,11,11,0.10)` | `rgba(255,255,255,0.10)` |
| Accent (selection, focus ring, primary series) | `--accent` | `#2a78d6` | `#3987e5` |
| Link text and primary button | `--link` | `#1b5aa6` | `#5a9ceb` |
| Good (price went down), text | `--good` | `#006300` | `#0ca30c` |
| Good, icon | `--good-icon` | `#0ca30c` | `#0ca30c` |
| Critical (price went up, failed run) | `--critical` | `#d03b3b` | `#d03b3b` |
| Warning (suspect snapshot, stale data) | `--warning` | `#fab219` | `#fab219` |
| Warning text on a light plane | `--warning-ink` | `#6b4a00` | `#fab219` |

`--warning-ink` is an addition to spec 8.1: `#fab219` is too light for text on the light plane, so warning text uses a darker shade. `--link` is also an addition (ADR-0006 (e), see below). It is kept in release 1.1 for in-app links (navigation, "See all", "Open Changes", table links) and the primary button, although the public build has no outbound links.

Dark mode is declared twice, under `@media (prefers-color-scheme: dark)` for `:root:not([data-theme='light'])` and under `:root[data-theme='dark']`. The theme toggle (light, dark, system) sets `data-theme`, so the toggle wins over the system setting.

Layout tokens: `--radius: 6px`; spacing `--s1` 8 px, `--s2` 16 px, `--s3` 24 px, `--s4` 32 px, `--s5` 48 px; `--max: 1440px`.

## Categorical colours (spec 8.2)

Fixed slots, never cycled. Colour follows the entity: filtering never recolours the survivors.

| Slot | Token | Light | Dark | Assigned to |
|---|---|---|---|---|
| 1 blue | `--cat-1` | `#2a78d6` | `#3987e5` | The selected or primary series; promo "Najlepsza oferta z rocznika 2026" (`bo`) |
| 2 orange | `--cat-2` | `#eb6834` | `#d95926` | Promo "Audi Q7 Final Edition" (`fe`) |
| 3 aqua | `--cat-3` | `#1baf7a` | `#199e70` | Promo "Leasing 101%" (`l101`) |
| 4 yellow | `--cat-4` | `#eda100` | `#c98500` | Promo "Pakiet ubezpieczeń za 1 zł" (`pu`) |
| 5 magenta | `--cat-5` | `#e87ba4` | `#d55181` | Promo "Oferta Business Edition" (`be`) |
| 6 green | `--cat-6` | `#008300` | `#008300` | reserved |
| 7 violet | `--cat-7` | `#6250d6` | `#9085e9` | Badge "Dodatkowe 15 000 zł korzyści" (`p15`) |
| 8 red | `--cat-8` | `#e34948` | `#e66767` | reserved |
| Other | `--cat-other` | `#898781` | `#898781` | Folded engine groups, de-emphasised models |

The promo-to-slot mapping is `color_slot` in `rules/promo_rules.yaml`.

Engine groups on a model page take slots 1-5 in the fixed order TFSI, TDI, TFSI quattro, TDI quattro, e-hybrid / e-tron. A group outside that list takes the next free slot; a model with more than five groups folds the rest into "Other" (slot 0). The assignment is computed by the collector (`assign_engine_slots` in `collector/collector/lifecycle.py`) and stored as `engine_slots` in the public `models/<slug>.json` (also `slot` per engine series) and in the private `meta/models.json`.

Comparing many models at once uses emphasis: the chosen model in slot 1, the others in muted grey, never 53 colours.

## Sequential and diverging scales (spec 8.2)

| Scale | Use | Tokens |
|---|---|---|
| Sequential blue, steps 100-700 | Magnitude, e.g. a discount % heatmap by model x engine group (no chart uses it yet) | `--seq-100` `#cde2fb`, `--seq-200` `#a3c8f5`, `--seq-300` `#74a9ec`, `--seq-400` `#4a8ce0`, `--seq-500` `#2a78d6`, `--seq-600` `#1b5aa6`, `--seq-700` `#0d366b` |
| Diverging blue to red | Price change | Blue and red ends with grey midpoint `--div-mid`: `#f0efec` light, `#383835` dark |

## Chart rules (spec 8.3)

- One y-axis per chart. Two measures of different scale are two charts or an index to 100.
- Lines 2 px, round-capped. Markers at least 8 px with a 2 px surface ring. Bars at most 24 px with 4 px rounded data-ends and 2 px surface gaps. Area fills at about 10 % opacity. Gridlines are solid hairlines.
- A legend is shown for two or more series; a single series has none. Direct labels only on the endpoint or the extreme. Axis ticks are compact (120K).
- Text never wears a series colour. Identity comes from a colour key beside the text.
- Every line chart has a crosshair tooltip listing all series at the hovered date, value first. Bars have per-mark tooltips. The same works on keyboard focus.
- Every chart has a table view: the configuration table, or a "Show data" toggle (`ShowData` in `web/src/components/common.tsx`).
- Status colours are only for status (freshness, run state, price direction with an arrow icon and a label), never for a series.
- Colour follows the entity.

Charts live in `web/src/charts/`: `TrendChart`, `RangeChart`, `PromoMixChart`, `Sparkline`, all on the shared `EChart` wrapper and `theme.ts`.

### Deviation: PromoMixChart uses grouped bars

Spec 7.1 and 7.4 describe the promo mix as stacked bars. `PromoMixChart` draws grouped bars instead: one bar per promo per snapshot, side by side. Promos overlap, since one offer can carry several badges, so a stack would read as parts of a whole and its total would exceed the offer count. The dataviz rules reserve stacks for parts of a whole. Colours, 24 px bar width, rounded data-ends and surface gaps are as specified. In release 1.1 the bars show badge counts per snapshot (`promo_counts`); a snapshot where the model has fewer than 3 offers has no counts. See ADR-0007; the deviation is still open against spec 7.4 (ADR-0006, Release 1.1 (e)).

## Palette validator

`web/tools/validate_palette.js` is the dataviz skill's validator, copied unchanged (spec 8.3). `web/tools/check_tokens.js` reads the eight `--cat-*` slots for light and dark from `tokens.css` and runs the validator for each mode against the matching surface (`#fcfcfb` light, `#1a1a19` dark). It exits non-zero when any check fails.

```text
cd web
npm run palette        # node tools/check_tokens.js
```

The validator computes lightness band, chroma floor, CVD separation, normal-vision floor and contrast against the surface. Result on 13 Oct 2026:

| Mode | Result | Notes |
|---|---|---|
| Light | All checks pass | Contrast vs surface is a WARN (relief band): `#1baf7a` 2.74, `#eda100` 2.11, `#e87ba4` 2.62 are below 3:1 |
| Dark | All checks pass | All eight slots at least 3:1 against the surface |

The light-mode contrast relief is legal only with a secondary encoding. That is why every chart has a table view and a legend, and why promo chips carry their name as text. Run the validator whenever `tokens.css` changes; `ci.yml` runs it in light and dark (spec 10.1).

## Type, layout and voice (spec 8.4)

| Area | Rule | Where |
|---|---|---|
| Typeface | IBM Plex Sans only, self-hosted through `@fontsource/ibm-plex-sans`, latin and latin-ext subsets, weights 400, 500, 600 | `web/src/main.tsx`, `--font` |
| Scale | 12 / 14 / 16 / 20 / 28 / 40 px; body 16 px with line height 1.45 | `web/src/styles/base.css` |
| Figures | `tabular-nums` only in tables and axes (`.num`); proportional figures elsewhere, including KPI values | `base.css` |
| Grid | Left-aligned, max content width 1440 px, 12 columns, 8 px spacing scale | tokens |
| Shape | One border radius (6 px), no drop shadows, no gradients, no decorative icons | |
| Structure | Dividers group, chips classify, numbering only where there is a sequence. No all-caps eyebrows, no middle-dot meta strings, no arrows appended to links, no monospace for data labels | |
| Memorable element | The model board on the Overview: one tile per model with a sparkline, in the site's own order | |
| Motion | One page-load reveal of the model board; otherwise only motion that answers an action. `prefers-reduced-motion` disables it | |
| Copy | Sentence case, active verbs, buttons name the action ("Export CSV"), errors say what happened and what to do, empty states invite the next action. Site-native terms stay in Polish and are explained once in About | |
| Brand | No Audi logo, wordmark, rings or AudiType font. Model names and promo wording are plain text. The source is named as plain text in About (spec 8.4) | `web/src/pages/About.tsx` |
| Outbound links | None. Neither build renders a link to audi.pl or to any page of the source; the public build fetches only its own `data/` (spec 7.5, 10.2). The e2e tests assert that no rendered page holds such a link | `web/e2e/` |
| Numbers and dates | `Intl.NumberFormat('pl-PL')`, `Intl.DateTimeFormat('pl-PL')`; UI labels in English | `web/src/lib/format.ts` |

## Contrast fixes found by Lighthouse (2026-10-13)

Spec 8.1 assigns the accent `#2a78d6` to links, but as link text it is 4.2:1 on the page plane, below WCAG 2.2 AA (4.5:1) required by spec 11. Link text and the primary button use `--link` (`#1b5aa6`, step 600 of the same blue ramp; `#5a9ceb` in dark mode). The muted grey `#898781` is 3.4:1 as small text, so it is kept for chart axes and gridline labels only; secondary text uses `--ink-2`. After the change Lighthouse (desktop) scores accessibility 100 on Overview, Model, Deals, Changes and About; see ADR-0006.
