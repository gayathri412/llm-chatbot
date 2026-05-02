from dataclasses import dataclass

from app.security import estimate_tokens


@dataclass(frozen=True)
class TokenLimitResult:
    text: str
    original_tokens: int
    final_tokens: int
    trimmed: bool


TRIM_NOTICE = "\n\n[Content trimmed to stay within token limit.]\n\n"


def trim_to_token_budget(text: str, max_tokens: int | None) -> TokenLimitResult:
    text = text or ""
    original_tokens = estimate_tokens(text)

    if not max_tokens or max_tokens <= 0 or original_tokens <= max_tokens:
        return TokenLimitResult(text, original_tokens, original_tokens, False)

    max_chars = max(0, max_tokens * 4)
    if max_chars <= len(TRIM_NOTICE):
        trimmed_text = text[:max_chars]
    else:
        usable_chars = max_chars - len(TRIM_NOTICE)
        head_chars = max(1, int(usable_chars * 0.65))
        tail_chars = max(1, usable_chars - head_chars)
        trimmed_text = f"{text[:head_chars]}{TRIM_NOTICE}{text[-tail_chars:]}"

    return TokenLimitResult(
        trimmed_text,
        original_tokens,
        estimate_tokens(trimmed_text),
        True,
    )
