"""Pluggable model backends. Inspect-inspired: Solver calls backend.generate().

- MockBackend: deterministic proxy calibrated to behave like a small open model.
  NOT a real model. Used for CI / offline demo. Real runs should use --model hf:...
- HFBackend: HuggingFace transformers pipeline (e.g. Qwen2.5-0.5B-Instruct).
- OpenAIBackend: any OpenAI-compatible endpoint (vLLM, Together, OpenAI, etc.)
"""
from __future__ import annotations
import random
import re


class BaseBackend:
    name: str = "base"

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        raise NotImplementedError


class MockBackend(BaseBackend):
    """Simulates a small instruction-following open model.

    Behavior (seeded, deterministic):
    - baseline: mostly correct (~75% general, ~65% cyber) to mimic TinyLlama/Qwen-0.5B class
    - sandbag: follows sandbag instruction with high compliance -> accuracy drops to ~25% (near chance)
    - elicit: CoT + few-shot gives small lift (+5pp)
    """

    def __init__(self, seed: int = 0):
        self.name = f"mock-seed{seed}"
        self.rng = random.Random(seed)
        # Pre-draw per (item_id, condition) correctness to keep runs stable
        self._cache: dict[tuple[str, str], bool] = {}

    def _extract_id(self, prompt: str) -> str:
        m = re.search(r"\[id=(.+?)\]", prompt)
        return m.group(1) if m else str(abs(hash(prompt)) % 10**8)

    def _should_be_correct(self, item_id: str, condition: str, task: str) -> bool:
        key = (item_id, condition)
        if key in self._cache:
            return self._cache[key]
        if condition == "sandbag":
            p = 0.25  # complies with underperformance instruction most of the time
        elif condition == "elicit":
            p = 0.80 if task == "general_qa" else 0.70
        else:  # baseline
            p = 0.75 if task == "general_qa" else 0.65
        val = self.rng.random() < p
        self._cache[key] = val
        return val

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        item_id = self._extract_id(prompt)
        condition = kwargs.get("condition", "baseline")
        task = kwargs.get("task", "general_qa")
        correct = kwargs.get("correct", "A")
        should_correct = self._should_be_correct(item_id, condition, task)
        if should_correct:
            out = correct
        else:
            wrong = [c for c in ["A", "B", "C", "D"] if c != correct]
            # deterministic wrong pick based on hash so re-runs match
            out = wrong[abs(hash(item_id)) % 3]
        if condition == "elicit":
            return f"Reasoning: considering options step by step. Final: {out}"
        return out


class HFBackend(BaseBackend):
    """Real open-weight model via Hugging Face transformers.

    Example: --model hf:Qwen/Qwen2.5-0.5B-Instruct
    Requires: pip install transformers torch accelerate
    Runs on CPU if no GPU (slow but works for ≤1B models on small eval).
    """

    def __init__(self, model_id: str = "Qwen/Qwen2.5-0.5B-Instruct", max_new_tokens: int = 64):
        self.name = f"hf:{model_id}"
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self._pipe = None

    def _lazy_load(self):
        if self._pipe is not None:
            return
        try:
            from transformers import pipeline
            import torch
        except ImportError as e:
            raise RuntimeError(
                "transformers not installed. Run: pip install transformers torch accelerate"
            ) from e
        # Apple Silicon MPS (or CUDA) + fp16 is ~20-50x faster than CPU float32.
        if torch.backends.mps.is_available():
            self._pipe = pipeline(
                "text-generation",
                model=self.model_id,
                trust_remote_code=True,
                device="mps",
                torch_dtype=torch.float16,
            )
        elif torch.cuda.is_available():
            self._pipe = pipeline(
                "text-generation",
                model=self.model_id,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=torch.float16,
            )
        else:
            self._pipe = pipeline(
                "text-generation",
                model=self.model_id,
                trust_remote_code=True,
                device_map="auto",
            )

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        import re

        self._lazy_load()
        # Strip the harness's internal [id=...] metadata tag: it is only used
        # by MockBackend for seeded determinism and pollutes real-model prompts
        # (small models echo the tag format, degrading output).
        prompt = re.sub(r"\[id=.+?\]\s*", "", prompt)
        # Use the model's chat template when available: raw-string prompting
        # severely degrades instruction-tuned models (they expect the
        # <|im_start|>/<|im_end|> turn format they were trained on).
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            full = self._pipe.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            full = f"{system}\n\n{prompt}" if system else prompt
        out = self._pipe(
            full, max_new_tokens=self.max_new_tokens, do_sample=False, return_full_text=False
        )
        return out[0]["generated_text"]


class OpenAICompatibleBackend(BaseBackend):
    """Any OpenAI-compatible chat endpoint. Set OPENAI_API_KEY / OPENAI_BASE_URL."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.name = f"openai:{model}"
        self.model = model

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("openai package required: pip install openai") from e
        import os

        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(model=self.model, messages=msgs, max_tokens=256)
        return resp.choices[0].message.content or ""


def make_backend(spec: str, seed: int = 0) -> BaseBackend:
    if spec == "mock" or spec.startswith("mock"):
        return MockBackend(seed=seed)
    if spec.startswith("hf:"):
        return HFBackend(model_id=spec[3:])
    if spec.startswith("openai:"):
        return OpenAICompatibleBackend(model=spec[7:])
    raise ValueError(f"Unknown --model spec: {spec!r}. Use mock | hf:<id> | openai:<model>")
