# Evaluation outputs

JSON / Markdown / CSV logs from **`scripts/run_eval.py`**, **`scripts/run_iterative_eval.py`**, **`compare_protocols.py`**, **`pa_bin_comparison.py`**, **`aggregate_runs.py`**, **`train_move_probe.py`**, and offline baselines.

## What is tracked in Git

The repo **`.gitignore`** ignores `evaluation_outputs/*` except the files listed below (canonical runs referenced in `docs/EXPERIMENT_RUNS.md` and the paper). Pilot/smoke files remain ignored.

| Artifact | Description |
|----------|-------------|
| `oracle_levels_eval.json` | Oracle (BFS), 65 levels |
| `random_seed42.json` | Random baseline |
| `openai_*.json`, `gpt4o_*.json` | `gpt-4o-mini` and `gpt-4o`: Protocol A/B, SC+retry, easy 2-shot |
| `gpt54mini_*.json`, `gpt54_*.json` | `gpt-5.4-mini` and `gpt-5.4`: Protocol A (65), Protocol B (20) |
| `trained_probe_summary.json` | Supervised next-move baseline |
| `*_qual_debug.json` | Optional qualitative `--debug` runs |
| `protocol_comparison*.md` | A vs B summaries |
| `pa_bin_comparison.md` | Bin table source (Markdown) |
| `summary.csv`, `iterative_ablation_summary.csv` | Aggregates |

Regenerate missing pieces using commands in **`docs/EXPERIMENT_RUNS.md`** and **`README.md`**.
