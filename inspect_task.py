"""Native UK AISI Inspect task (optional). Requires: pip install inspect-ai.

Run:
  inspect eval inspect_task.py --model mockllm/model
  inspect eval inspect_task.py --model hf/Qwen/Qwen2.5-0.5B-Instruct

This mirrors run_eval.py's sandbagging conditions using Inspect's
@task / dataset / solver / scorer primitives.
"""
try:
    from inspect_ai import task, Task
    from inspect_ai.dataset import json_dataset
    from inspect_ai.solver import system_message, generate
    from inspect_ai.scorer import choice
except ImportError:  # pragma: no cover
    raise RuntimeError("pip install inspect-ai to use this file")

from src.conditions import CONDITIONS


@task
def sandbag_general() -> Task:
    return Task(
        dataset=json_dataset("evals/general_qa.jsonl"),
        solver=[system_message(CONDITIONS["baseline"]), generate()],
        scorer=choice(),
    )


@task
def sandbag_general_sandbag() -> Task:
    return Task(
        dataset=json_dataset("evals/general_qa.jsonl"),
        solver=[system_message(CONDITIONS["sandbag"]), generate()],
        scorer=choice(),
    )


@task
def cyber_proxy_baseline() -> Task:
    return Task(
        dataset=json_dataset("evals/cyber_proxy.jsonl"),
        solver=[system_message(CONDITIONS["baseline"]), generate()],
        scorer=choice(),
    )
