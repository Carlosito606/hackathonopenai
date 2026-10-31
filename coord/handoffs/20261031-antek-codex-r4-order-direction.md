agent: antek-codex   rocket: R4 TIMELINE   branch: r4/order-direction

Scope: temporal question ordering only, based on main dc59bf0. Independent of count-extraction PR #24.
Descending lists now reverse; quoted titles and alternatives cannot set direction/output type. Contradictory
explicit directions defer to the baseline reader. Source facts still expose ascending chronology.

Checks: 99 tests, py_compile and diff checks pass. Full 107-question temporal dev-minus-holdout plan comparison
against frozen 42ab798: every R1/R4 plan identical, with 12 computations. No reader accuracy improvement claimed.
Comparison details live in /tmp/r4-order-direction-plan-audit.json; no raw data/caches/predictions included.

Ongoing work: full paired temporal reader stays frozen at 42ab798 in r4-chunk-manifest. Count extraction V4
ran on committed 5ebc2d2 in r4-count-extraction; inspect /tmp/r4-counting-probe-v4.json for its terminal result.
Keep the benchmark worktree unchanged while its supervisor/reader/worker are live. The bridge remains active.
No R4 Reactor calls: the final R1 reservation lasts until 08:15 UTC unless mission control releases it.
Next: finish temporal reader scoring/audit and validate counting semantics/coverage on dev before default use.
