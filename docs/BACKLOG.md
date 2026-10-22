Covers: owner decisions, the state of the release 1.1 implementation and follow-up work (spec 15.1, spec 16, release 2 candidates).
Last verified against the code: 2026-10-13.

# Backlog

## Release 1.1: public trends edition (spec 16)

The implementation is done. The go-public steps of spec 16.5 are in progress: until they are complete, `rlgdev/audilitics` stays private and the Pages site is not switched on. The release 1.0 repository is never made public, because its history holds VINs, the raw feed and the Audi bundle.

| Spec | Item | State |
|---|---|---|
| 16.1 | Collector: redaction at ingestion, slider counts per model, no bundle download, canonical order and `offer_id`, configuration analytics, minimum group size, private and public trees, publication guard and identifier check, User-Agent with the public repository URL, private-only exports | Done |
| 16.2 | Dashboard: `VITE_EDITION` with one routes module, configuration tables in the public build, offer table, Car and Dealers in the private build, no links to audi.pl, hot panel and Changes on configurations, e2e screenshots from synthetic data | Done |
| 16.3 | Repositories and workflows: `deploy-pages.yml` and `ci.yml` in the public repository with the guard; `collect.yml` and `ci.yml` in the private repository; Makefile `DATA`, `EDITION`, `FIXTURE=real`, `guard` | Done in code; the private repository, its workflows and `PUBLIC_REPO_TOKEN` are set up with 16.5 |
| 16.4 | Data migration: redacted 13 Oct 2026 raw file and fixture (`collector/tools/redact_raw_1_0.py`), rebuild in the private repository, release 1.0 data removed from the codebase, synthetic fixture | Done |
| 16.5 | Going public: rename the 1.0 repository, create the private and the new public repository, token, one forced run, guard and public-history check, then public visibility and Pages ([runbook](runbook.md#going-public-spec-165)) | In progress |
| 16.6 | Documentation: README, data source, data model, analytics, runbook, design plan, changelog, backlog | Done |

## Owner decisions (spec 15.1)

| # | Item | State | Where it is defined |
|---|---|---|---|
| 1 | Contact in the User-Agent and who receives automation issues | Decided: public repository URL, no e-mail; issues in the private repository | Spec 4.2, 15.1 |
| 2 | Repository visibility and site access | Decided: public repository and Pages site with aggregates only; private repository for offers; fresh public history | Spec 10.4, 16.5, ADR-0009 |
| 3 | Legal check of collecting the feed | Decided: trends only, no identifiers or links, minimum group size 3, publication guard | Spec 11 (Legal), ADR-0009 |
| 4 | Cadence anchor and an extra run at month start | Cadence decided in spec rev 39: every Monday (6-day guard). Open: the extra month-start run; manual runs via `workflow_dispatch` | `collect.yml` (private), `min_snapshot_age_days` |
| 5 | UI language | Open. Default: English labels, Polish site terms | `web/src` |
| 6 | Dealer phone numbers | Decided: not collected | Spec 3.5 |
| 7 | Spec 12.1 Business Edition badge count (2,617 → 2,847) | Done in spec rev 38 | Spec 12.1, ADR-0006 |
| 8 | Public name “Audilitics” (contains the Audi trade mark) | Open. Default: keep, with the non-affiliation notice; rename before going public if preferred | Spec 15.1 |

## Release 2 candidates (spec 13)

- Slack or Teams digest of hot deals after each run
- Alert rules per model (median price below a threshold), weekly cadence
