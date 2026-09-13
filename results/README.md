# Results

Canonical run: `python run_eval.py --model mock --seed 1` → `results.json` (150 trials).

- general_qa: baseline 73.33% [0.57, 0.90] → sandbag 26.67% [0.10, 0.43] → elicit 86.67% [0.73, 0.97]
- cyber_proxy: baseline 65.00% [0.45, 0.85] → sandbag 40.00% [0.20, 0.60] → elicit 85.00% [0.65, 1.00]
- sandbag_gap_general +46.66pp, sandbag_gap_cyber +25.00pp
- elicit_lift_general +13.34pp, elicit_lift_cyber +20.00pp
- selectivity −21.66pp (generic prompt = uniform drop, not selective hiding)

Interpretation: eval scores are highly prompt-malleable; black-box point scores understate
both the floor (under sandbag pressure) and the ceiling (under elicitation). To claim a
finding on a real open model, re-run with `--model hf:Qwen/Qwen2.5-0.5B-Instruct` and replace
this file. See `METHODOLOGY.md` §4–5 for validity notes.
