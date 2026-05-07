# Rush Hour LLM Planning Eval

A Rush Hour planning benchmark with a strict simulator, BFS oracle baseline, and OpenAI model evaluation.

## What this repo includes

- `game/`: board parsing, legal move generation, simulator, BFS solver
- `llm/`: OpenAI client, prompt builders, output parsing
- `evaluation/`: baselines/helpers
- `scripts/`: CLI entrypoints for eval and analysis
- `prompts/`: protocol rules and few-shot examples
- `data/`: committed eval sets (`levels_eval.json`, `levels_easy_40.json`, etc.)
- `tests/`: unit tests
- `evaluation_outputs/`: saved JSON/CSV/Markdown run artifacts

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.
```

Create a local `config.yaml` (gitignored) like:

```yaml
llm:
  provider: openai
  model: gpt-4o-mini
```

Set `OPENAI_API_KEY` in `.env` or your shell.

## Quick checks (offline)

```bash
pytest -q

python scripts/run_eval.py --planner oracle --levels data/levels_eval.json \
  --out evaluation_outputs/oracle_levels_eval.json

python scripts/run_eval.py --planner random --levels data/levels_eval.json --seed 42 \
  --out evaluation_outputs/random_seed42.json
```

## Protocol A (single-shot full plan)

```bash
python scripts/run_eval.py --planner openai --config config.yaml \
  --levels data/levels_eval.json --sleep-between-levels 0.5 \
  --out evaluation_outputs/openai_levels_eval.json
```

Other model configs used in this project:
- `config.gpt4o.yaml`
- `config.gpt54mini.yaml`
- `config.gpt54.yaml`

## Protocol B (iterative one-move, matched N=20)

```bash
python scripts/run_iterative_eval.py --planner openai --config config.yaml \
  --levels data/levels_eval.json --max-levels 20 --max-steps 500 \
  --sleep-seconds 0.35 \
  --out evaluation_outputs/openai_iterative_20.json
```

## Compare Protocol A vs B

```bash
python scripts/compare_protocols.py \
  --protocol-a evaluation_outputs/openai_levels_eval.json \
  --protocol-b evaluation_outputs/openai_iterative_20.json \
  --out evaluation_outputs/protocol_comparison.md
```

## Notes

- `run_eval.py` defaults to running all levels in the file unless `--max-levels` is set.
- Use `--max-levels` for low-cost smoke tests before full runs.
- Saved run artifacts are under `evaluation_outputs/`.
