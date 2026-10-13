# ADR-0008: Derived files are a pure function of the snapshots

Status: Accepted, 2026-10-13.

Context: Runs must be idempotent and replayable, and running the same date twice must leave `data/` byte-identical (spec 11, spec 12.1). Incremental updates of trends, histories and changes would make the result depend on the order of runs and replays.

Decision: Everything under `data/` except `raw/` and `snapshots/` is rebuilt from all `ok` snapshots, `snapshots/index.json` and `rules/` on every run (`rebuild()` in `collector/collector/indexes.py`). The model directory, vehicle histories, trends, changes, deals, dealers, `latest.json` and `manifest.json` are recomputed from scratch, and stale model and changes files are deleted. Files are written deterministically and only when their bytes change.

Consequences: A replay, a status override or a rules change shows up everywhere after one rebuild. `suspect` snapshots are excluded by skipping them. Run time grows with the number of snapshots, which is acceptable at one snapshot per 14 days.

Update for release 1.1: the rule now covers both trees. `rebuild()` writes the private files (`data/private/`, `data/meta/`) and `public.py` writes `data/public/`, deleting files of earlier runs that are no longer part of it. Vehicle histories are gone (offers have no identity across runs, spec 5.5); configuration histories take their place. Dealer statistics are private.
