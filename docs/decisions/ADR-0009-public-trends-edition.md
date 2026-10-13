# ADR-0009: Public trends edition: aggregates only, no identifiers

Status: Accepted, 2026-10-13 (spec rev 38).

Context: Release 1.0 collects every car with its VIN, offer link and dealer phone and would publish offer-level tables on a public GitHub Pages site. The audi.pl Regulamin (§8.2–8.3) forbids commercial use of the site’s information and its reproduction or publication without written consent; the database right covers making a substantial part of a database available to the public; a VIN can become personal data once a car is registered. The owner wants a public repository and no legal exposure (spec 15.1).

Decision:
(a) Collect without identifiers: `vin`, `komisja`, `link`, `kod_audi` and `telefon` are dropped right after schema validation, with no hashes kept (spec 3.5).
(b) Publish aggregates only: trends, model statistics and configuration-level deal scores; every public figure rests on at least 3 offers (spec 5.5).
(c) Two repositories: public `rlgdev/audilitics` (code, rules, docs, aggregates, Pages) and private `rlgdev/audilitics-private` (scheduled collector, redacted offers, exports, reports). The private dashboard is a local build and is never deployed (spec 7, 9, 10).
(d) A publication guard blocks identifiers, links to audi.pl, dealers, unknown files and small groups before every push and deploy (spec 10.5).
(e) No links to audi.pl anywhere, no copies of the site’s bundle, no brand assets.
(f) The release 1.0 repository is never made public; the public repository starts with a fresh history (spec 16.5).

Consequences: Collection rests on the text-and-data-mining exception for databases (art. 8a ustawy o ochronie baz danych) while no machine-readable reservation exists; publication stays below re-use of the database and outside §8.3 because nothing is reproduced at offer level. A single car can no longer be followed across runs, so changes, momentum, the like-for-like index and hot deals work on configurations; per-car price history, days listed and dealer moves are gone. Per-offer slider flags are replaced by badge rules plus per-model slider counts. Dealers appear only in the private build. A reservation found later, an objection from Volkswagen Group Polska or a block (403, 429) stops collection until the owner decides.
