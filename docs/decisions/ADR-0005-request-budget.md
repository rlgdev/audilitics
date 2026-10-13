# ADR-0005: Request budget of 10 per run

Status: Accepted, 2026-10-13.

Context: Spec 2 and spec 11 cap a run at 10 HTTP requests. Spec 3.1 and 4.2 list an index page, two directories, the main pull, six slider pulls, a `get-filtered.php` cross-check and a bundle download: more than 10.

Decision: The 10 budgeted requests are the index page, `data_models2.json`, `data_dealers2.json`, the main `get2.php` pull and six slider pulls (`bo`, `fe`, `l101`, `pu`, `be`, `pks`). The `get-filtered.php` cross-check is dropped to stay inside the budget; per-model counts are computed from the main pull. The bundle is downloaded only when its hash is new, and that request is logged as unbudgeted (`counted: false`). Retries of the main pull are not counted again. `request_budget: 10` lives in `collector/config.yaml`.

Consequences: A normal run makes exactly 10 requests, and 11 on a run with a new bundle. Adding a slider needs a budget decision first; a request beyond the budget fails the run. The run report shows a "Budgeted" column per request.

Update for release 1.1 (spec rev 38, 3.1, 4.2): the bundle is never downloaded. The hash is read from the file name on the index page and recorded, so every run makes exactly the 10 budgeted requests. Slider responses are reduced to item counts per model in memory.
