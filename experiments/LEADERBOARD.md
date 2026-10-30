# Fleet scoreboard (mission control only)

Stand-in model for local end-to-end runs: <one model for the whole team, e.g. Qwen2.5-7B-Instruct 4-bit>.
Splits: dev minus `splits/dev_holdout.txt` (local), `splits/reactor_mini.txt` (Reactor), `splits/dev_hard*` (POLIGON).
Retrieval column: all gold sessions in the evidence, per type (k-update / multi / ss-asst / ss-user / temporal).

## Rockets

| sync | rocket | run_id | retrieval (ku / ms / ssa / ssu / tr) | local correct | abstain ok | evidence F1 | dev-hard | Reactor mini |
|---|---|---|---|---|---|---|---|---|

## Parts announced [PART-READY]

| sync | rocket | stage | wins on | numbers | adopted by |
|---|---|---|---|---|---|

## Ship candidates (docking)

| candidate | stages per question type | local | dev-hard | Reactor mini | holdout (once) |
|---|---|---|---|---|---|
