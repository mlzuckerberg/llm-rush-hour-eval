# Level format

## Fogleman database line

Text files such as [`rush1000.txt`](https://www.michaelfogleman.com/static/rush/rush1000.txt) and the full `rush.txt` use:

```text
OPTIMAL_MOVES BOARD36 [CLUSTER_ID]
```

- `OPTIMAL_MOVES`: minimum number of slides (each slide moves one piece any distance until blocked), under the same no consecutive same-piece search restriction as [fogleman/rush `solver.go`](https://github.com/fogleman/rush/blob/master/solver.go) (see `docs/PROJECT_LOG.md`).
- `BOARD36`: row-major 6×6 characters:
  - `o` or `.` — empty (this codebase accepts `o` in data files)
  - `x` — wall
  - `A`–`Z` — vehicles; same letter = one rigid piece (car length 2 or truck 3 inferred from geometry)
- `CLUSTER_ID` (optional): metadata from the database; ignored by the simulator.

## JSON used in this repo

`data/sample_levels.json` is a list of objects:

```json
{"id": "string", "optimal_moves": int, "board": "36 chars", "cluster": int}
```

`scripts/prepare_dataset.py` can build larger splits from a downloaded `rush.txt`.

Easier slice for ablations: `data/levels_easy_40.json` — same schema as `levels_eval.json`, filtered to `optimal_moves` ≤ 40 (built by `scripts/build_easy_subset.py`).

## LLM move notation

One move per line in model output:

```text
LETTER STEPS
```

- `LETTER`: the piece label as shown on the board (`A`–`Z`), not the internal index.
- `STEPS`: signed integer along that piece’s axis (horizontal: negative = left, positive = right; vertical: negative = up, positive = down).

Example: `B +2` slides piece `B` two cells in the forward direction for that orientation.
