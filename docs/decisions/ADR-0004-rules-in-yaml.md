# ADR-0004: Promo, plan and scoring rules in versioned YAML

Status: Accepted, 2026-10-13.

Context: The badge, footnote and plan rules come from an unofficial source (the site bundle) and change when the site deploys. Each snapshot must be reproducible with the rules valid on its date (spec 2, spec 4.5).

Decision: Keep the rules in `rules/promo_rules.yaml`, `rules/plans.yaml` and `rules/scoring.yaml` as lists of complete rule sets, each with a `version` and a `valid_from` date. A snapshot is processed with the newest set whose `valid_from` is on or before its date (`collector/collector/rules.py`). Model overrides live in `rules/models.yaml`. Rules are transcribed by a person, never parsed from the bundle (spec 3.6).

Consequences: A rule change is a reviewed data change, not a code change. Old rule sets are never edited; a change adds a new set. `make rebuild` reprocesses history on purpose. The rules version string (`promo:v1/plans:v1/scoring:v1`) is recorded per snapshot.
