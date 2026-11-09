import asyncio
import json

import pytest

from app.offline import rule_based_refine
from app.providers import LLMProvider, ProviderError
from app.refiner import Refiner, parse_llm_json, word_diff


# ---------- offline rules ----------
def test_offline_formal_expands_and_fixes():
    out = rule_based_refine("hi sir, i dont know teh answer pls help", "formal")
    assert out["refined"] == "Hello sir, I do not know the answer please help."
    types = {c["type"] for c in out["corrections"]}
    assert {"spelling", "tone", "capitalization", "punctuation", "word_choice"} <= types


def test_offline_family_keeps_contractions():
    out = rule_based_refine("i cant come tmrw , will call u", "family")
    assert out["refined"] == "I can't come tomorrow, will call you."
    assert all(c["type"] != "tone" for c in out["corrections"])


def test_offline_clean_text_has_no_corrections():
    out = rule_based_refine("I will call you tomorrow.", "family")
    assert out["refined"] == "I will call you tomorrow."
    assert out["corrections"] == []


# ---------- JSON parsing ----------
def test_parse_plain_and_fenced_json():
    payload = {"refined": "Hi.", "corrections": [], "tip": ""}
    assert parse_llm_json(json.dumps(payload)) == payload
    assert parse_llm_json("```json\n" + json.dumps(payload) + "\n```") == payload
    assert parse_llm_json("Sure! Here it is: " + json.dumps(payload) + " Hope it helps.") == payload


def test_parse_rejects_non_json():
    with pytest.raises(ValueError):
        parse_llm_json("I cannot help with that.")


# ---------- diff ----------
def test_word_diff_rebuilds_both_texts():
    a, b = "i has a apple.", "I have an apple."
    diff = word_diff(a, b)
    assert "".join(s.text for s in diff if s.op != "insert") == a
    assert "".join(s.text for s in diff if s.op != "delete") == b
    assert any(s.op == "insert" for s in diff) and any(s.op == "delete" for s in diff)


# ---------- refiner with a fake model ----------
class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, replies):
        super().__init__(model="test")
        self.replies = list(replies)
        self.calls = 0

    async def generate(self, system, user):
        self.calls += 1
        return self.replies.pop(0)


def test_refiner_normalizes_model_output():
    reply = json.dumps({
        "refined": "I have completed the assignment.",
        "corrections": [
            {"original": "has completed", "corrected": "have completed", "type": "Grammar", "explanation": "Use 'have' with 'I'."},
            {"original": "x", "corrected": "x", "type": "spelling"},          # no change -> dropped
            {"original": "assigment", "corrected": "assignment", "type": "typo"},  # unknown type -> other
        ],
        "tip": "Use 'have' with I, you, we and they.",
    })
    provider = FakeProvider([reply])
    result = asyncio.run(Refiner(provider).refine("I has completed the assigment.", "formal"))
    assert result.refined == "I have completed the assignment."
    assert [c.type for c in result.corrections] == ["grammar", "other"]
    assert result.provider == "fake · test"


def test_refiner_retries_once_then_fails():
    provider = FakeProvider(["not json", "still not json"])
    with pytest.raises(ProviderError):
        asyncio.run(Refiner(provider).refine("hello", "family"))
    assert provider.calls == 2


def test_refiner_succeeds_on_retry():
    provider = FakeProvider(["oops", json.dumps({"refined": "Hello!", "corrections": [], "tip": ""})])
    result = asyncio.run(Refiner(provider).refine("hello", "family"))
    assert result.refined == "Hello!"
