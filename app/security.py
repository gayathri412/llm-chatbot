import hashlib
import math
import re
from dataclasses import dataclass


EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redacted: bool
    counts: dict[str, int]


def hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def redact_pii(text: str) -> RedactionResult:
    counts = {"emails": 0, "phones": 0}

    def replace_email(match):
        counts["emails"] += 1
        return "[REDACTED_EMAIL]"

    def replace_phone(match):
        counts["phones"] += 1
        return "[REDACTED_PHONE]"

    redacted_text = EMAIL_PATTERN.sub(replace_email, text or "")
    redacted_text = PHONE_PATTERN.sub(replace_phone, redacted_text)

    return RedactionResult(
        text=redacted_text,
        redacted=any(counts.values()),
        counts=counts,
    )
