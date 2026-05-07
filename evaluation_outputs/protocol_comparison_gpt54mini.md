# Protocol A vs B (matched level ids)
- **Protocol A file:** `evaluation_outputs/gpt54mini_levels_eval.json`
- **Protocol B file:** `evaluation_outputs/gpt54mini_iterative_20.json`
- **Levels compared:** 20 (intersection of ids)
- **Protocol B options (from JSON header):** `self_consistency_k=1`, `retry_on_illegal=False`

## Headline metrics
| Metric | Protocol A (single-shot) | Protocol B (iterative) |
|--------|---------------------------|-------------------------|
| Win rate | 0.000 | 0.000 |
| First move legal rate | 0.000 | — |
| Mean legal prefix length (before stop) | 0.00 | 0.10 |
| Mean API calls per level | 1.0 | 1.10 |

## Protocol B — distribution of `applied_moves` (legal moves before failure or cap)
| applied_moves | Count |
|---------------|-------|
| 0 | 18 |
| 1 | 2 |

## By optimal-move bin (same ids as above)
| Bin | n | A win | B win | B mean applied |
|-----|---|-------|-------|----------------|
| 38-42 | 18 | 0.000 | 0.000 | 0.11 |
| 43-47 | 2 | 0.000 | 0.000 | 0.00 |
