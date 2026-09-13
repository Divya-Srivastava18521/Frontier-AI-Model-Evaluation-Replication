"""Simple analysis: bootstrap 95% CIs + printable table."""
from __future__ import annotations
import random


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def bootstrap_ci(correct: list[int], n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(correct)
    if n == 0:
        return (0.0, 0.0)
    stats = []
    for _ in range(n_boot):
        sample = [correct[rng.randrange(n)] for _ in range(n)]
        stats.append(mean(sample))
    stats.sort()
    lo = stats[int(0.025 * n_boot)]
    hi = stats[int(0.975 * n_boot) - 1]
    return (round(lo, 4), round(hi, 4))


def report_table(summary: dict, trials_by_key: dict[str, list[int]] | None = None) -> str:
    lines = []
    lines.append(f"{'task/condition':<24}{'n':>5}{'acc':>8}  95% CI")
    for k in sorted(summary):
        if k.startswith("_"):
            continue
        v = summary[k]
        ci = ""
        if trials_by_key and k in trials_by_key:
            lo, hi = bootstrap_ci(trials_by_key[k])
            ci = f" [{lo:.2f}, {hi:.2f}]"
        lines.append(f"{k:<24}{v['n']:>5}{v['accuracy']:>8.2%}{ci}")
    lines.append("")
    lines.append("Key metrics:")
    for k, v in summary.get("_metrics", {}).items():
        lines.append(f"  {k}: {v:+.2%}" if isinstance(v, float) else f"  {k}: {v}")
    return "\n".join(lines)
