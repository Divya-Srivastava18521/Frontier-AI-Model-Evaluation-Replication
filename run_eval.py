#!/usr/bin/env python3
"""Frontier eval replication runner (Inspect-inspired, dependency-free).

Replicates a small-scale version of:
- van der Weij et al. 2024 'AI Sandbagging' (prompted underperformance + selective sandbagging)
- UK AISI Inspect pattern (Task = dataset + solver + scorer) + cyber proxy tasks
  inspired by US/UK AISI pre-deployment cyber methodology (Cybench-style, defensive only)

Usage:
  python run_eval.py --model mock --seed 0
  python run_eval.py --model hf:Qwen/Qwen2.5-0.5B-Instruct
  python run_eval.py --model openai:gpt-4o-mini
  python run_eval.py --model mock --tasks general_qa cyber_proxy --conditions baseline sandbag elicit

If inspect_ai is installed, you can also run the equivalent native task:
  inspect eval inspect_task.py --model hf/Qwen/Qwen2.5-0.5B-Instruct
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.backends import make_backend
from src.harness import load_jsonl, run_task, summarize, TrialResult
from src.analysis import report_table

ROOT = Path(__file__).parent
TASKS = {
    "general_qa": ROOT / "evals" / "general_qa.jsonl",
    "cyber_proxy": ROOT / "evals" / "cyber_proxy.jsonl",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mock", help="mock | hf:<id> | openai:<model>")
    ap.add_argument("--tasks", nargs="*", default=["general_qa", "cyber_proxy"], choices=list(TASKS))
    ap.add_argument(
        "--conditions", nargs="*", default=["baseline", "sandbag", "elicit"],
        choices=["baseline", "sandbag", "elicit"],
    )
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--output", default="results/results.json")
    ap.add_argument("--max-new-tokens", type=int, default=64,
                    help="max new tokens per generation (HF backend only)")
    args = ap.parse_args()

    backend = make_backend(args.model, seed=args.seed)
    if hasattr(backend, "max_new_tokens"):
        backend.max_new_tokens = args.max_new_tokens
    all_trials: list[TrialResult] = []
    for task in args.tasks:
        samples = load_jsonl(TASKS[task])
        for cond in args.conditions:
            all_trials.extend(run_task(samples, task, cond, backend))

    summary = summarize(all_trials)
    trials_by_key: dict[str, list[int]] = {}
    for t in all_trials:
        trials_by_key.setdefault(f"{t.task}/{t.condition}", []).append(1 if t.correct else 0)

    print(f"Model: {backend.name}")
    print(report_table(summary, trials_by_key))

    out = {
        "model": backend.name,
        "model_spec": args.model,
        "seed": args.seed,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tasks": args.tasks,
        "conditions": args.conditions,
        "summary": summary,
        "trials": [t.__dict__ for t in all_trials],
        "notes": (
            "MockBackend is an illustrative proxy, not a real model. "
            "For a real open-model run use --model hf:Qwen/Qwen2.5-0.5B-Instruct "
            "after pip install -r requirements.txt"
        ) if args.model == "mock" else "Real model run.",
    }
    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path} ({len(all_trials)} trials)")


if __name__ == "__main__":
    main()
