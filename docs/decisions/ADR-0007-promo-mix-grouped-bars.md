# ADR-0007: PromoMixChart uses grouped bars, not stacked bars

Status: Accepted, 2026-10-13.

Context: Spec 7.1 and 7.4 describe the promo mix per snapshot as stacked bars. Promos overlap: one car can carry several. On 13 Oct 2026, 4,675 of 4,768 cars had the Leasing 101% slider tag and 2,847 the Business Edition tag, so a stack would far exceed the stock. The dataviz rules (spec 8.3) reserve stacks for parts of a whole.

Decision: `web/src/charts/PromoMixChart.tsx` draws grouped bars: one bar per promo per snapshot, side by side, in the promo's fixed colour slot, with one tooltip per snapshot listing every promo. Bar width, rounded data-ends and surface gaps follow spec 8.3.

Consequences: Each bar reads as "cars with this promo", and no stack implies a total larger than the stock. The "Show data" table view holds the exact counts.

Update for release 1.1: the chart shows badge counts per run (offers carrying each card badge), because slider membership needs an identifier and is no longer set on offers (spec 3.4, 5.2). Badges overlap just as slider tags did, so the bars stay grouped.
