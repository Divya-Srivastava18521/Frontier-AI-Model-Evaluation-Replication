# Frontier AI Model Evaluation Replication: Sandbagging + Cyber Proxy

A small-scale replication of published frontier-model safety evaluations on an open model,
built with UK AISI's **Inspect** evaluation pattern (`Task = dataset + solver + scorer`).

**Primary source replicated:** van der Weij et al. (2024) *"AI Sandbagging: Language Models can
Strategically Underperform on Evaluations"* (ICLR 2025) — prompted underperformance +
selective sandbagging on dangerous-capability vs. general-capability evals.
**Framework:** UK AISI **Inspect AI** (+ Inspect Evals / Cybench-style cyber methodology from the
US/UK AISI joint pre-deployment test of Claude Sonnet 3.5).
**Context:** Apollo Research scheming / strategic-deception evals (evaluation awareness, sandbagging).

> Safety note: all cyber tasks here are **defensive, benign proxies** (password hygiene, phishing
> recognition, Linux fundamentals, secure coding). No exploit instructions, no disallowed content.
> This measures *evaluation-steerability*, not real offensive capability.

## Results (mock proxy, seed 1, 150 trials)

| task/condition | n | acc | 95% CI |
|---|---|---:|---|
| general_qa / baseline | 30 | 73.33% | [0.57, 0.90] |
| general_qa / elicit | 30 | 86.67% | [0.73, 0.97] |
| general_qa / sandbag | 30 | 26.67% | [0.10, 0.43] |
| cyber_proxy / baseline | 20 | 65.00% | [0.45, 0.85] |
| cyber_proxy / elicit | 20 | 85.00% | [0.65, 1.00] |
| cyber_proxy / sandbag | 20 | 40.00% | [0.20, 0.60] |

Key metrics:
- `sandbag_gap_general`: +46.66pp (baseline − sandbag) — model is highly steerable to underperform
- `sandbag_gap_cyber`: +25.00pp
- `elicit_lift_general`: +13.34pp, `elicit_lift_cyber`: +20.00pp (CoT + few-shot upper bound)
- `selectivity`: −21.66pp (generic sandbag prompt drops *both* suites; selective hiding needs a targeted prompt — consistent with the original paper)

`MockBackend` is an illustrative proxy, not a real model. Swap in a real open-weight model
for the actual finding (one flag — see below).

## Quickstart

```bash
# 1. Demo run (zero dependencies, offline)
python run_eval.py --model mock --seed 1

# 2. Real open-model run (Qwen 0.5B, CPU-ok)
pip install -r requirements.txt
python run_eval.py --model hf:Qwen/Qwen2.5-0.5B-Instruct

# 3. Any OpenAI-compatible endpoint (vLLM / Together / OpenAI)
export OPENAI_API_KEY=... OPENAI_BASE_URL=...
python run_eval.py --model openai:gpt-4o-mini

# 4. Native Inspect (optional)
pip install inspect-ai
inspect eval inspect_task.py --model mockllm/model
```

## Repo layout

```
evals/general_qa.jsonl    30 benign general-knowledge MCQs (harmless-capability suite)
evals/cyber_proxy.jsonl   20 defensive cyber-fundamentals MCQs (safe dangerous-capability proxy)
evals/persuasion.jsonl     5 benign persuasion prompts (qualitative only, not scored for risk)
src/conditions.py         baseline / sandbag / elicit system prompts (from van der Weij et al.)
src/backends.py           MockBackend | HFBackend (transformers) | OpenAICompatibleBackend
src/harness.py            Inspect-inspired Task runner: dataset -> solver -> scorer
src/analysis.py           bootstrap 95% CIs + summary table
run_eval.py               CLI entry point, writes results/results.json
inspect_task.py           native Inspect @task wrappers for the same evals
results/results.json      canonical run output (mock, seed 1)
METHODOLOGY.md            full write-up: mapping to papers, threats to validity, ethics
```

## What this replicates (and what it doesn't)

Replicates: prompted-sandbagging steerability test (can the model follow an instruction to
underperform?), capability-elicitation lift (does CoT/few-shot raise the ceiling?), and the
Inspect Task/solver/scorer structure + cyber-proxy suite shape from AISI methodology.
Does NOT replicate: password-locked fine-tuning (needs training), agentic CTF solving
(needs sandbox + Cybench), or real hazardous-capability measurement (deliberately out of scope).

See `METHODOLOGY.md` for the paper-by-paper mapping, limitations, and how to extend to a
real `Qwen/Mistral/Llama` run for your write-up.
