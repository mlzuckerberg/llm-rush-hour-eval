# Protocol A vs B (matched level ids)
- **Protocol A file:** `evaluation_outputs/openai_levels_eval.json`
- **Protocol B file:** `evaluation_outputs/openai_iterative_20.json`
- **Levels compared:** 20 (intersection of ids)
- **Protocol B options (from JSON header):** `self_consistency_k=1`, `retry_on_illegal=False`

## Headline metrics
| Metric | Protocol A (single-shot) | Protocol B (iterative) |
|--------|---------------------------|-------------------------|
| Win rate | 0.000 | 0.000 |
| First move legal rate | 0.050 | — |
| Mean legal prefix length (before stop) | 0.05 | 0.25 |
| Mean API calls per level | 1.0 | 1.25 |

## Protocol B — distribution of `applied_moves` (legal moves before failure or cap)
| applied_moves | Count |
|---------------|-------|
| 0 | 16 |
| 1 | 3 |
| 2 | 1 |

## By optimal-move bin (same ids as above)
| Bin | n | A win | B win | B mean applied |
|-----|---|-------|-------|----------------|
| 38-42 | 18 | 0.000 | 0.000 | 0.28 |
| 43-47 | 2 | 0.000 | 0.000 | 0.00 |
