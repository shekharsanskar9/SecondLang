"""Core logic: send text to the model, clean up its answer and compute a word-level diff."""
from __future__ import annotations

import difflib
import json
import re

from .offline import rule_based_refine
from .prompts import CORRECTION_TYPES, build_system_prompt, build_user_prompt
from .providers import LLMProvider, OfflineProvider, ProviderError
from .schemas import Correction, DiffSegment, RefineResponse

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_TOKEN_RE = re.compile(r"\s+|\w+(?:['’]\w+)*|[^\w\s]")


def parse_llm_json(raw: str) -> dict:
    """Extract the JSON object from a model reply, tolerating code fences or extra prose."""
    text = _FENCE_RE.sub("", (raw or "").strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("The model did not return JSON.")
        data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("The model returned JSON, but not an object.")
    return data


def word_diff(original: str, refined: str) -> list[DiffSegment]:
    """Word-level diff: equal / delete (only in original) / insert (only in refined)."""
    a, b = _TOKEN_RE.findall(original), _TOKEN_RE.findall(refined)
    segments: list[DiffSegment] = []

    def push(op: str, tokens: list[str]) -> None:
        text = "".join(tokens)
        if not text:
            return
        if segments and segments[-1].op == op:
            segments[-1].text += text
        else:
            segments.append(DiffSegment(op=op, text=text))

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            push("equal", a[i1:i2])
        else:
            push("delete", a[i1:i2])
            push("insert", b[j1:j2])
    return segments


def _clean_corrections(items) -> list[Correction]:
    result = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        original = str(item.get("original", "")).strip()
        corrected = str(item.get("corrected", "")).strip()
        if not (original or corrected) or original == corrected:
            continue
        kind = str(item.get("type", "other")).strip().lower().replace(" ", "_")
        result.append(Correction(
            original=original,
            corrected=corrected,
            type=kind if kind in CORRECTION_TYPES else "other",
            explanation=str(item.get("explanation", "")).strip(),
        ))
    return result


class Refiner:
    def __init__(self, provider: LLMProvider, native_language: str = "Hindi", retries: int = 1):
        self.provider = provider
        self.native_language = native_language
        self.retries = retries

    async def _ask_model(self, text: str, tone: str, context: str | None) -> dict:
        system = build_system_prompt(tone, self.native_language)
        user = build_user_prompt(text, context)
        last_error: Exception | None = None
        for _ in range(self.retries + 1):
            raw = await self.provider.generate(system, user)
            try:
                return parse_llm_json(raw)
            except ValueError as exc:  # json.JSONDecodeError is a ValueError
                last_error = exc
        raise ProviderError(f"The model's answer could not be read ({last_error}). Please try again.")

    async def refine(self, text: str, tone: str, context: str | None = None) -> RefineResponse:
        if isinstance(self.provider, OfflineProvider):
            data = rule_based_refine(text, tone)
        else:
            data = await self._ask_model(text, tone, context)

        refined = str(data.get("refined") or "").strip() or text
        return RefineResponse(
            original=text,
            refined=refined,
            tone=tone,
            context=context or None,
            corrections=_clean_corrections(data.get("corrections")),
            tip=str(data.get("tip") or "").strip(),
            diff=word_diff(text, refined),
            provider=self.provider.label,
        )
