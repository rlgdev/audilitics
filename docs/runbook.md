Covers: operating the collector of the private repository: commands, issue labels, failed, blocked and suspect runs, schema changes, guard failures, the rules review on the live bundle, the reservation check, replay and rebuild, forced runs, the PUBLIC_REPO_TOKEN, model overrides, going public and the public-history check (spec 3.6, 4, 10, 11, 16.5).
Last verified against the code: 2026-10-13.

# Runbook

The collector runs as the job `collect.yml` of the private repository `rlgdev/audilitics-private`, every Monday at 05:17 UTC with a 13-day guard, so one snapshot is taken every second Monday (spec 4.1). The job checks out the public repository at `COLLECTOR_REF` (repository variable, default `main`), collects into the private `data/`, runs the publication guard and the identifier check, commits `data/` to the private repository, mirrors `data/public/` onto `data/` of `rlgdev/audilitics` with the `PUBLIC_REPO_TOKEN` and opens or updates issues (spec 10.1). Issues, run reports and job artifacts live in the private repository only. The push to the public repository triggers `deploy-pages.yml`.

Locally, clone both repositories side by side (`audilitics/` and `audilitics-private/`) and run every command from the root of the public clone after `make setup`.

## Commands (spec 4.4)

Each `make` target is a thin wrapper around the collector CLI (`collector/collector/cli.py`), run as `PYTHONPATH=collector python -m collector`.

| Make target | CLI equivalent |
|---|---|
| `make collect DATA=<dir>` | `python -m collector --data-dir <dir> collect` (live run, 10 requests) |
| `make collect FORCE=1 DATE=YYYY-MM-DD DATA=<dir>` | `... collect --force --date YYYY-MM-DD` |
| `make collect FROM=<file> DATA=<dir>` | `... collect --from <file>` (replay one redacted raw file) |
| `make collect FIXTURE=1` | `python -m collector --data-dir build/fixture-data collect --fixture synthetic` |
| `make collect FIXTURE=real DATA=<dir>` | `... collect --fixture real` (reads `../audilitics-private/fixtures/2026-10-13/raw.json.gz`, or `AUDILITICS_REAL_FIXTURE`) |
| `make rebuild DATA=<dir>` | `... rebuild` |
| `make guard` / `make guard GUARD_DIR=<dir>` | `python -m collector guard data` / `python -m collector guard <dir>` |
| `make idcheck DATA=<dir>` | `python -m collector idcheck <dir>`; add `--public` to treat `offer_id` keys as identifiers too |
| `make issues DRY=1` | `python -m collector issues --dry-run` |

`DATA` defaults to `../audilitics-private/data` (`build/fixture-data` with `FIXTURE=1`). `collect` and `rebuild` exit 1 when a run is `failed`; `guard` and `idcheck` exit 1 on any finding.

Each run also writes `.run/result.json` and `.run/report.md` next to `data/` (for example `audilitics-private/.run/`). They hold the status, gates, warnings and the issues to open. `python -m collector issues` reads `result.json` and creates or updates one GitHub issue per label with the GitHub CLI; an open issue with the same label gets a comment instead of a duplicate (spec 4.3). A run that stores a snapshot also writes its report to `data/reports/<date>.md`.

## Issue labels (spec 4.3, 9.1)

| Label | Raised when | Section |
|---|---|---|
| `collector-failure` | Network or HTTP error, JSON parse error, missing known field, `count != len(items)` after retries, request budget exhausted, or a `suspect` snapshot | [Failed run](#failed-run-collector-failure), [Suspect snapshot](#suspect-snapshot) |
| `collector-blocked` | HTTP 403 or 429 | [Blocked run](#blocked-run-collector-blocked) |
| `schema-change` | The feed sends a field that is not in the schema | [Schema change](#schema-change) |
| `rules-review` | The bundle hash differs from the previous snapshot’s, or a slider count differs from its badge count by more than 1 % | [Rules review](#re-verifying-rules-after-a-bundle-change) |
| `publication-guard` | The publication guard or the identifier check fails | [Guard failure](#guard-failure-publication-guard) |

## Failed run (collector-failure)

A failed fetch or schema run writes nothing under `data/`: no snapshot, no raw archive, no derived file. Nothing is committed or pushed and the previous site stays online (spec 11, Reliability). The run report goes to `.run/`, which the job uploads as an artifact.

1. Open the issue and the job artifact (`.run/report.md`). The status line gives the message.
2. Read the request log at the bottom of the report: path, status, bytes, time and whether each request was budgeted.
3. Decide the cause:

| Message | Likely cause | Action |
|---|---|---|
| `<path>: HTTP 5xx`, `<path>: ConnectionError`, `<path>: Timeout` | Site outage | Wait a few hours, then force one run |
| `get2.php: count N != M items` | The site changed data during the pull | Force one run later |
| `<what>: JSON parse error` | The endpoint returned HTML or changed format | Open the endpoint in a browser; if the format changed, treat it as a schema change |
| `schema: item N: missing known field(s) ...` | Schema change | See [Schema change](#schema-change) |
| `request budget of 10 exhausted before <path>` | A code or rules change added requests | Fix the code or the slider list; see ADR-0005 |

4. When the cause is fixed, [force one run](#forcing-a-run). Close the issue by hand; nothing closes it automatically.

## Blocked run (collector-blocked)

HTTP 403 or 429 stops the run at the request that got it, with no retry (spec 4.3). A block stops collection until the owner decides (spec 11, Legal).

1. Stop. Do not re-run the job, do not dispatch it again, and do not work around the block: no other address, network, proxy or User-Agent, no change of spacing, back-off or budget to push through.
2. Disable the schedule: in `rlgdev/audilitics-private`, Actions, workflow `collect`, menu "…", Disable workflow.
3. Check the politeness of the last run in its report: at most 10 budgeted requests, 1 s apart, the User-Agent naming the public repository, and only one run (the job uses `concurrency: collector`).
4. Record the facts in the issue and tell the owner.
5. Only the owner decides whether collection resumes. If it does, enable the workflow again and force one run. If that run is blocked as well, stop again and go back to the owner.

## Suspect snapshot

A run whose offer count is below 80 % of the previous `ok` run is stored with status `suspect` and raises a `collector-failure` issue (spec 4.3). It is archived in the private repository (`raw/`, `snapshots/`) but excluded from every derived file and every public figure. The public `snapshots/index.json` lists it with date and status only, and the dashboard shows a warning strip.

1. Check whether the drop is real: open gotowedoodbioru.audi.pl and compare the stock count with the report. The site opens with the best-offer slider on, which hides about half of the stock; switch it off first.
2. If the drop is not real (a partial answer), do nothing. The next run is compared with the last `ok` run and the suspect snapshot stays out. Close the issue by hand.
3. If the drop is real, mark the snapshot `ok`. In the private checkout, edit its entry in `data/snapshots/index.json`:

```json
{
  "date": "2026-10-27",
  "status": "ok",
  "status_set_by": "maintainer",
  "offers": 2861,
  "...": "leave the other fields as they are"
}
```

4. Run `make rebuild DATA=../audilitics-private/data`. The rebuild keeps every entry with `status_set_by` and, when the count gate says `suspect` again on that date, keeps `ok` and adds the warning "status kept as ok: set by a maintainer in index.json".
5. Commit `data/` to the private repository (a pull request runs its `ci.yml`) and close the issue. The public repository receives the rebuilt public tree with the next run that pushes (spec 10.3).

The override works in one direction only: a computed `suspect` is promoted to `ok` when `status_set_by` is `maintainer`. A hand-set `"status": "suspect"` on a snapshot that passes the count gate is overwritten with `ok` on the next replay or rebuild.

## Schema change

A **new field** gives an `ok` snapshot with a warning and a `schema-change` issue.

- A field whose name or value looks identifying (spec 4.3; the rule is in `docs/data-source.md`) is dropped at ingestion and listed under "dropped as identifying". It is never stored, so its earlier values cannot be recovered.
- Any other new field is kept in `extra` on each offer and in the raw items.

1. Look at the field in the private `data/raw/<date>.json.gz` (`feed.items[*]`).
2. If it is useful, add it to `KEPT_FIELDS` and `FeedItem` in `collector/collector/schema.py`, map it in `collector/collector/normalise.py` and `collector/schemas/offer.schema.json`, document it in `docs/data-source.md`, and update the synthetic fixture (`collector/tests/fixtures/synthetic/generate.py`, then `expected.py`) in one pull request.
3. Run `make rebuild DATA=../audilitics-private/data` so earlier snapshots get the typed field where the raw data has it.

If a kept field turns out to be an identifier, add its name to `discarded_fields` in `collector/config.yaml` and raise it with the owner (spec 3.5 lists the discarded fields). Then re-archive each affected raw file: copy it out of `data/raw/` and replay the copy with `make collect FROM=<copy> DATA=../audilitics-private/data`; a file outside `data/raw/` is archived again, redacted. Earlier commits of the private repository still hold the value; tell the owner.

A **missing known field** fails the run (`collector-failure`); the raw file is not archived, so a fix needs a new live run. The five discarded fields count as known: they are checked for presence before they are dropped.

1. Decide whether the field was renamed or removed (compare a live item with the field dictionary).
2. Update `schema.py` (and `DISCARDED` in `redact.py` for a discarded field), `normalise.py`, the docs and the fixture in one pull request (the PR template asks for this).
3. Force one run.

## Guard failure (publication-guard)

The publication guard checks the public tree; the identifier check covers all of the private `data/` (spec 10.5; the checks are listed in `docs/data-model.md`). They run in every collector job before the commit and the push. A failure sets the run to `failed`, opens a `publication-guard` issue with up to 100 findings, and nothing is committed or pushed; the previous site stays online. The guard also runs in the public repository’s `ci.yml` and before every Pages deploy, where a failure stops the deploy before the upload.

Findings read `<file>:<JSON path>: <problem>`, for example `dashboard/deals.json:$.configs[0].special_min: rests on fewer than 3 priced offers`.

| Problem | Likely cause | Fix |
|---|---|---|
| `VIN-shaped string` | A feed value, or a new field, holds a 17-character token of capitals and digits; in the private tree this includes exports and reports | Locate the value from the file and path of the finding. An identifier field goes into `discarded_fields` (see [Schema change](#schema-change)). Never loosen the pattern without the owner |
| `identifier key`, `dealer key` | A code change writes a forbidden key into the public tree | Fix `public.py` or `diff.py` and add a test |
| `link to audi.pl` | A URL of the source copied into a public file, from a rules text or a feed string | Remove it from `rules/*.yaml` or stop copying the string |
| `rests on fewer than 3 ... offers`, `statistic without its ... count` | A statistic written without the minimum group or without its `offers` / `priced` count | Fix `analytics.py` or `public.py` and add a test |
| `file outside the public layout` | A new file in `data/public/`, or a file added to the public `data/` by hand | Remove it. A new public file needs a change of spec 5.3, `PUBLIC_LAYOUT` in `guard.py` and `public.py` |

1. Read the findings in the issue or in `.run/report.md`.
2. Reproduce with the current code in the private checkout: `make rebuild DATA=../audilitics-private/data`, then `make guard GUARD_DIR=../audilitics-private/data/public` and `make idcheck DATA=../audilitics-private/data`. A failure caused by the new run’s own data does not reproduce this way, because the job did not commit its raw file; work from the findings.
3. Fix the cause in a pull request to the public repository, with a test; `make test` must pass.
4. After the merge (the job runs the collector from `COLLECTOR_REF`), force one run and close the issue by hand.

Never loosen the guard to make a run pass, never push a public tree by hand and never edit `data/` of the public repository by hand: it is written only by the collector job.

When a local run fails the guard, its files are already in `DATA` (snapshot, index entry with status `ok`, derived files, report). Discard them before anything else, in the private checkout: `git checkout -- data` and `git clean -fd data`.

When the public `ci.yml` or `deploy-pages.yml` fails the guard on `data/`, look for a commit that touched `data/` by hand and revert it. If the guard itself was tightened, fix the collector so the next run writes a passing tree, then force a run.

## Re-verifying rules after a bundle change

A `rules-review` issue is raised when the bundle hash changes ("Site bundle changed on <date>", old and new hash) or when a slider total differs from its badge total by more than 1 % ("Slider and badge counts differ on <date>", for example `l101: slider 4675 vs badge 4800`). The snapshot status is unchanged (spec 4.3).

The bundle is never downloaded, archived or parsed automatically (spec 3.6). A person reads the rules on the live site, in a browser, as any visitor’s browser loads them:

1. Open gotowedoodbioru.audi.pl in Chrome or Edge, open the developer tools (F12), Network panel, reload, and filter on `main.`. Check that the hash in the file name matches the issue.
2. Open the file in the Sources panel and pretty-print it (`{}`). Search (Ctrl+F) for each identifier below and compare what you find with the YAML.

| Search for | Compare with |
|---|---|
| `leasing101PercentModels2026` (and `leasing101BadgeModels2026`) | `badges.l101.models_by_production_year` in `rules/promo_rules.yaml` |
| `additional15000BenefitModels` | `badges.p15.model_code_prefixes` |
| `finalEditionModels` (and `isFinalEdition`) | `badges.fe` and `sliders.fe` |
| `updateOfferPackageType` (and `offerPackageType`) | `badges.pu.package_rules` |
| `isBestOffer` | `badges.bo` |
| `rateAnnotationNumber` | `footnote_rules` and `footnote_2_exception` in `rules/plans.yaml` |

   Also check the card template expression near `business_edition`: on 13 Oct 2026 it showed the Business Edition badge when `business_edition == "Tak" && !isFinalEdition` (ADR-0006).
3. Do not save the file, do not copy it or long excerpts into the repository, an issue, a chat or any other file. Note only the rule values you compare (model lists, code prefixes, years).
4. For a slider warning, compare per model: the private `snapshots/<date>.json.gz` holds `slider_counts`, and the public `trends.json` holds `slider_counts` and `promo_counts` per model. On the site, switch one slider on (and the others off) and read the number of results.
5. Repeat the [reservation check](#reservation-check-spec-36) and record its result in the issue.
6. If nothing changed, close the issue with a comment naming the hash and the date of the check.
7. If something changed, add a **new** rule set. Never edit an old one: snapshots before the change must keep the rules valid on their date (spec 4.5).

```yaml
rule_sets:
  - version: v1
    valid_from: 2026-10-13
    # ... unchanged ...
  - version: v2
    valid_from: 2026-11-10        # the date of the first snapshot with the new bundle
    source_bundle: main.<hash>.js
    # full copy of v1 with the changes applied
```

   A rule set is selected as the newest one with `valid_from` on or before the snapshot date. Each rule set is complete: copy the previous set and change it, do not write a diff. `rules/plans.yaml` works the same way.
8. Add or update a unit test in `collector/tests/test_rules.py`, update `docs/data-source.md` and the rules versions in `docs/CHANGELOG.md`, and merge the pull request after `make test`.
9. In the private checkout, run `make rebuild DATA=../audilitics-private/data`, check the sliders gate in the newest report, and commit `data/`. The next run pushes the public tree.

Normalisation (badges, plan codes) uses the rule set of each snapshot’s date. Scoring and the plan parameters in the derived files use the rule set of the newest `ok` snapshot.

## Reservation check (spec 3.6)

Repeat it at every rules review and whenever the owner asks. Use a browser; no scripts and no downloads.

| Check | How | 13 Oct 2026 |
|---|---|---|
| `robots.txt` of the subdomain | Open `/robots.txt` on gotowedoodbioru.audi.pl | No file |
| TDM reservation file | Open `/.well-known/tdmrep.json` on the same host | No file |
| TDM headers | Developer tools, Network: response headers of the index page and of one `get2.php` request; look for `tdm-reservation` and `tdm-policy` | None |
| Robots meta tag | View the source of the index page; search for `<meta name="robots"` and `<meta name="tdm-reservation"` | None |
| Main domain | Open `robots.txt` of `www.audi.pl` | Disallows only `/userinfo/` |

A reservation is, for example: a `tdmrep.json` entry with `"tdm-reservation": 1` covering `/` or `/ajax/`; a `tdm-reservation: 1` header; a `tdm-reservation` meta tag with content `1`; a `robots.txt` rule that disallows `/` or `/ajax/` for all agents or for `audilitics`; any explicit text reserving text and data mining. When unsure, treat it as a reservation.

If a reservation is found, stop collection the same day: disable `collect` in the private repository, record the finding in the issue and tell the owner. There are no further runs until the owner decides (spec 11, Legal). The same applies to a written objection from Volkswagen Group Polska. The owner also decides what happens to the published aggregates.

## Replaying a run

`make collect FROM=../audilitics-private/data/raw/2026-10-27.json.gz DATA=../audilitics-private/data` processes an archived redacted raw file again with the rules valid on its date. It rewrites that date’s snapshot, index entry and report and rebuilds every derived file, private and public. The Excel export and `latest.csv` are rewritten only when the date is the newest `ok` snapshot. A raw file outside `data/raw/` (for example a fixture) is redacted and archived into `data/raw/`.

Add `DATE=YYYY-MM-DD` (workflow input `date`) to store the replay under another date. `make collect FIXTURE=real DATA=../audilitics-private/data` replays the redacted 13 Oct 2026 fixture. Replaying the same file twice leaves both trees byte-identical (spec 12.1).

## make rebuild

`make rebuild DATA=../audilitics-private/data` replays every `data/raw/*.json.gz` in date order. Use it after a rules, scoring or normalisation change, or after a maintainer status edit.

1. It resets `data/snapshots/index.json` to the entries that carry `status_set_by`, then replays each raw file.
2. Each replay rewrites the snapshot and rebuilds the derived files. Because they are a pure function of the `ok` snapshots and `rules/` (ADR-0008), the result is the same as if history had been collected with the current code.
3. Review the diff of `data/` before committing it to the private repository. Same inputs give byte-identical files, so an unexpected diff means a behaviour change.

The public repository receives the rebuilt tree with the next run that pushes (spec 10.3).

## Forcing a run

The job skips with status `skipped` when the newest snapshot is younger than 13 days (spec 4.1).

- In GitHub: `rlgdev/audilitics-private`, Actions, workflow `collect`, Run workflow, set `force` to `true`. Leave `date` empty for today.
- Locally: `make collect FORCE=1 DATA=../audilitics-private/data` makes a live run from your machine. It counts against the site like any run, and only the job commits and pushes; prefer the workflow.

Force one run at a time. A forced run on a date that already has a snapshot overwrites it (spec 11, Reliability).

## Rotating the PUBLIC_REPO_TOKEN

`PUBLIC_REPO_TOKEN` is the only secret (spec 11, Security): a fine-grained personal access token that can write the contents of `rlgdev/audilitics` and nothing else.

1. In GitHub: Settings, Developer settings, Personal access tokens, Fine-grained tokens, Generate new token.
2. Resource owner: the owner of `rlgdev/audilitics`. Repository access: Only select repositories, `rlgdev/audilitics`. Permissions: Repository permissions, Contents: Read and write (Metadata: Read-only is added automatically). No other permission. Set an expiry date and a reminder before it.
3. In `rlgdev/audilitics-private`: Settings, Secrets and variables, Actions, `PUBLIC_REPO_TOKEN`, Update secret.
4. Check that the next run’s log shows the push `data: trends <date>` to the public repository, then revoke the old token.

A token created before a repository rename stays bound to the renamed repository (spec 16.5 step 4). An expired or revoked token stops the job from pushing to the public repository; the site keeps the previous data until a run pushes again.

The repository variable `COLLECTOR_REF` (same settings page, Variables) selects the branch or tag of the public repository the job runs; set it to a tag to pin or roll back the collector.

## Merging a renamed model

When the site renames a model, the new name is added as a new model. If its offers carry the model-code prefix of a retired or empty model, the run report lists it under "New models" with "possible rename of <old name>" (spec 4.6).

1. Confirm on the site that it is the same model.
2. Add an override to `rules/models.yaml` in the public repository, keyed by the new name exactly as the feed sends it (example names):

```yaml
overrides:
  Audi Q6 Sportback e-tron quattro:
    merge_into: Audi Q6 Sportback e-tron
```

3. After the merge, run `make rebuild DATA=../audilitics-private/data` and commit `data/` to the private repository. Offers with the new name are counted under the old model, so its slug and trends continue.

`config_key` includes the model name as the feed sends it, so the configurations under the new name start new configuration histories; model, segment and total series continue.

## Manually retiring a model

Models retire on their own after `empty_runs_to_retire: 3` runs without offers (`collector/config.yaml`). To retire one earlier, or to keep one hidden:

```yaml
overrides:
  Audi A8:
    status: retired
```

Overrides win over discovery (spec 4.6). A model retired by override stays retired even when offers return; remove the override to let the automatic lifecycle take over again. The override sets only `status`; `retired_on` stays as computed. The other override fields are `slug`, `segment` (`A`, `Q`, `S/RS`, `e-tron`) and `order`. Changes take effect on the next run or after `make rebuild`.

## Going public (spec 16.5)

The release 1.0 repository holds VINs, the raw feed and the bundle in its history and is never made public. The public repository starts with a fresh history.

| Step | Action |
|---|---|
| 1 | Rename `rlgdev/audilitics` to `rlgdev/audilitics-1.0` and keep it private; delete it once release 1.1 has run successfully |
| 2 | Create `rlgdev/audilitics-private` (private) with `collect.yml` and `ci.yml`, and push the migrated data of spec 16.4 |
| 3 | Create a new `rlgdev/audilitics`, private for now, and push the release 1.1 tree as one fresh commit |
| 4 | Create the fine-grained token for the new repository (above) and store it as `PUBLIC_REPO_TOKEN` |
| 5 | Run `collect` once with `force: true` and read the run report; run `make guard` and the [public-history check](#public-history-check) on `rlgdev/audilitics` |
| 6 | Only then switch `rlgdev/audilitics` to public; set Settings, Pages, Source to "GitHub Actions" and Settings, Actions, General, Workflow permissions to read; run `deploy-pages` and check the site |

The current state of these steps is in `docs/BACKLOG.md`.

## Public-history check

The guard and the identifier check must pass on every commit of the public repository, so no commit ever held a raw feed, a bundle copy, an offer-level file or a VIN (spec 12.1). Run it in a fresh clone of `rlgdev/audilitics` after `make setup`, from its root, in bash (Git Bash on Windows):

```bash
PY=.venv/bin/python            # .venv/Scripts/python on Windows
tmp=$(mktemp -d)
status=0
for c in $(git rev-list --all); do
  rm -rf "$tmp/data"
  git cat-file -e "$c:data" 2>/dev/null || continue      # commit without data/
  git archive "$c" data | tar -x -C "$tmp"
  PYTHONPATH=collector "$PY" -m collector guard "$tmp/data" > "$tmp/out.txt" \
    || { echo "$c: guard failed"; cat "$tmp/out.txt"; status=1; }
  PYTHONPATH=collector "$PY" -m collector idcheck "$tmp/data" --public > "$tmp/out.txt" \
    || { echo "$c: identifier check failed"; cat "$tmp/out.txt"; status=1; }
done
echo "public history: $([ "$status" = 0 ] && echo pass || echo FAILED)"
```

Then list every path that any commit ever held where a raw feed, a bundle, an offer-level file, an export or the release 1.0 fixture would live. The expected output is empty:

```bash
git log --all --format= --name-only | sort -u \
  | grep -E '^data/(raw|vehicles|exports|reports|private)/|^data/snapshots/.+\.gz$|main\.[0-9a-f]+\.js$|\.xlsx$|^collector/tests/fixtures/2026-10-13/'
```

Run both before the repository goes public (step 5 above) and whenever a bad push is suspected.
