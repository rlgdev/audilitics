# ADR-0006: Deviations from the specification found during implementation

Status: Accepted, 2026-10-13.

Context: Building the collector and running it against the live feed of 13 Oct 2026 showed four places where the specification is wrong or ambiguous.

Decision:
(a) Business Edition badges are 2,847, not 2,617. Spec 12.1 expected 2,847 minus the 230 Final Edition cars. In the live feed none of the 230 Final Edition cars has `business_edition=Tak`, and the site's card template shows the Business Edition badge when `business_edition == "Tak" && !isFinalEdition`. The suppression is implemented but removes nothing, so the correct count is 2,847; `collector/tests/test_rules.py` asserts 2,847.
(b) `lowest_ever` uses a configuration key (sha1 of model, engine, model code, model year), not `version_key`. `version_key` includes `cena_vtp`, so every price change creates a new version and the flag would always be true.
(c) Snapshot files hold only per-date normalised observations. History-dependent fields (`price_change`, `rate_change`, `lowest_ever`) are computed when the derived files are rebuilt, so replaying any date is exact.
(d) The spec's "Business Edition without Final Edition" acceptance number in 12.1 should be corrected to 2,847.

Consequences: The acceptance test differs from spec 12.1 until the spec is amended. `lowest_ever` means "lowest price seen for this configuration". Snapshot files never need rewriting when history changes.

(e) Spec 8.1 colours links with the accent `#2a78d6` (4.2:1, fails WCAG AA for text). Links use a `--link` token (`#1b5aa6`, same blue ramp) and small secondary text uses secondary ink instead of the muted grey; chart marks and axes are unchanged.

## Release 1.1

Status: Accepted, 2026-10-13 (spec rev 38).

Context: Implementing the public trends edition (spec 16) showed five places where the code departs from the letter of spec rev 38.

Decision:
(a) The identifier check over the private tree does not treat `offer_id` as an identifier, because private files must hold offer ids (spec 5.1). Over a public tree it does, as spec 10.5 requires (`identifier_check(root, public=True)`, `python -m collector idcheck <dir> --public`; the publication guard always does).
(b) `new_config` is not set on the first `ok` run ever; otherwise every configuration would be flagged on day one. From the second `ok` run on it marks the first run in which a configuration is published (spec 6.3).
(c) The Business Edition slider-versus-badge gate (spec 4.3) compares the `b=Tak` slider with the number of offers carrying `business_edition=Tak`, not with the Business Edition badge, because that slider also returns Final Edition cars whose card shows only the Final Edition badge (spec 3.4).
(d) The migration of the release 1.0 raw file (`collector/tools/redact_raw_1_0.py`, spec 16.4) keeps the bundle name and hash in the redacted raw file; only the bundle download record and its request are dropped. Rules-review comparisons keep a baseline hash.
(e) `PromoMixChart` stays grouped bars (ADR-0007) although spec 7.4 still says stacked bars.

Consequences: Private files may carry `offer_id` and still pass the identifier check; public files never. The Changes and hot-deal views show no wave of new configurations after the first run. The Business Edition gate stays quiet when the badge and flag differ only by Final Edition cars. Spec 10.5 (a), 6.3 (b), 4.3 (c), 16.4 step 1 (d) and 7.4 (e) can be amended to match.
