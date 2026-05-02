import re
from dataclasses import dataclass
from typing import Any


DEFAULT_FORBIDDEN_TOPIC_PATTERNS = (
    r"\bmake\s+(?:a\s+)?bomb\b",
    r"\bbuild\s+(?:a\s+)?bomb\b",
    r"\b(?:kill|murder|assassinate)\s+(?:someone|a person|people)\b",
    r"\bself[-\s]?harm\b",
    r"\bsuicide\b",
    r"\b(?:steal|exfiltrate)\s+(?:passwords?|credentials?|api keys?)\b",
    r"\b(?:bypass|crack)\s+(?:login|password|authentication)\b",
    r"\bmalware\b",
    r"\bransomware\b",
)

DEFAULT_OUTPUT_MODERATION_PATTERNS = (
    r"\bhere(?:'s| is)\s+how\s+to\s+(?:make|build)\s+(?:a\s+)?bomb\b",
    r"\bsteps?\s+to\s+(?:kill|murder|assassinate)\b",
    r"\b(?:steal|exfiltrate)\s+(?:passwords?|credentials?|api keys?)\b",
    r"\bdeploy\s+(?:malware|ransomware)\b",
)

SAFE_COMPLETION = (
    "I can't help with that request. I can still help with safe, educational, "
    "or defensive information on the topic."
)


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str = ""
    matched_pattern: str = ""


@dataclass(frozen=True)
class ReferenceCheckResult:
    passed: bool
    reason: str = ""


def _split_patterns(value: str | None) -> list[str]:
    if not value:
        return []
    return [pattern.strip() for pattern in value.split("||") if pattern.strip()]


def _compile_patterns(patterns: list[str] | tuple[str, ...]) -> list[re.Pattern]:
    compiled = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            continue
    return compiled


def validate_prompt(
    prompt: str,
    custom_patterns: str | None = None,
    *,
    enabled: bool = True,
) -> GuardrailResult:
    if not enabled:
        return GuardrailResult(True)

    patterns = [*DEFAULT_FORBIDDEN_TOPIC_PATTERNS, *_split_patterns(custom_patterns)]
    for pattern in _compile_patterns(patterns):
        if pattern.search(prompt or ""):
            return GuardrailResult(
                False,
                reason="Prompt matched a forbidden topic rule.",
                matched_pattern=pattern.pattern,
            )

    return GuardrailResult(True)


def moderate_output(
    output: str,
    custom_patterns: str | None = None,
    *,
    enabled: bool = True,
) -> GuardrailResult:
    if not enabled:
        return GuardrailResult(True)

    patterns = [*DEFAULT_OUTPUT_MODERATION_PATTERNS, *_split_patterns(custom_patterns)]
    for pattern in _compile_patterns(patterns):
        if pattern.search(output or ""):
            return GuardrailResult(
                False,
                reason="Model output matched a moderation rule.",
                matched_pattern=pattern.pattern,
            )

    return GuardrailResult(True)


def _source_tokens(context_items: list[dict[str, Any]]) -> set[str]:
    tokens = set()
    for index, item in enumerate(context_items, start=1):
        tokens.add(f"[{index}]")
        for key in ("title", "source"):
            value = str(item.get(key) or "").strip()
            if value:
                tokens.add(value.lower())
    return tokens


def check_references(
    answer: str,
    context_items: list[dict[str, Any]],
    *,
    enabled: bool = True,
) -> ReferenceCheckResult:
    if not enabled or not context_items:
        return ReferenceCheckResult(True)

    answer_text = (answer or "").lower()
    if not answer_text.strip() or answer_text.startswith("error:"):
        return ReferenceCheckResult(True)

    for token in _source_tokens(context_items):
        if token and token.lower() in answer_text:
            return ReferenceCheckResult(True)

    return ReferenceCheckResult(
        False,
        "Answer used retrieved context but did not reference any retrieved title, source, or citation marker.",
    )


def append_reference_notice(answer: str, context_items: list[dict[str, Any]]) -> str:
    references = []
    for index, item in enumerate(context_items, start=1):
        title = str(item.get("title") or "Untitled").strip()
        source = str(item.get("source") or "unknown").strip()
        references.append(f"[{index}] {title} ({source})")

    if not references:
        return answer

    return f"{answer.rstrip()}\n\nReferences checked:\n" + "\n".join(references)
