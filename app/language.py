import re
from dataclasses import dataclass
from typing import Any


SCRIPT_RANGES = {
    "hi": ("Hindi", r"[\u0900-\u097F]"),
    "bn": ("Bengali", r"[\u0980-\u09FF]"),
    "pa": ("Punjabi", r"[\u0A00-\u0A7F]"),
    "gu": ("Gujarati", r"[\u0A80-\u0AFF]"),
    "ta": ("Tamil", r"[\u0B80-\u0BFF]"),
    "te": ("Telugu", r"[\u0C00-\u0C7F]"),
    "kn": ("Kannada", r"[\u0C80-\u0CFF]"),
    "ml": ("Malayalam", r"[\u0D00-\u0D7F]"),
    "ur": ("Urdu", r"[\u0600-\u06FF]"),
}

LATIN_HINTS = {
    "es": ("Spanish", {"que", "como", "para", "hola", "gracias", "por", "favor"}),
    "fr": ("French", {"bonjour", "merci", "avec", "pour", "comment", "quoi", "vous"}),
    "de": ("German", {"hallo", "danke", "und", "oder", "nicht", "bitte", "wie"}),
    "pt": ("Portuguese", {"ola", "obrigado", "obrigada", "como", "para", "voce"}),
}

STYLE_BY_CODE = {
    "en": "Use concise, professional English with clear bullets when helpful.",
    "hi": "Use simple, polite Hindi phrasing. Keep technical terms clear and avoid unnecessary English mixing.",
    "bn": "Use simple, polite Bengali phrasing with clear technical terms.",
    "pa": "Use simple, polite Punjabi phrasing with clear technical terms.",
    "gu": "Use simple, polite Gujarati phrasing with clear technical terms.",
    "ta": "Use simple, polite Tamil phrasing with clear technical terms.",
    "te": "Use simple, polite Telugu phrasing with clear technical terms.",
    "kn": "Use simple, polite Kannada phrasing with clear technical terms.",
    "ml": "Use simple, polite Malayalam phrasing with clear technical terms.",
    "ur": "Use simple, polite Urdu phrasing with clear technical terms.",
    "es": "Use clear, professional Spanish with concise structure.",
    "fr": "Use clear, professional French with concise structure.",
    "de": "Use clear, professional German with concise structure.",
    "pt": "Use clear, professional Portuguese with concise structure.",
}

LANGUAGE_NAME_TO_CODE = {
    "english": "en",
    "hindi": "hi",
    "hindii": "hi",
    "bengali": "bn",
    "punjabi": "pa",
    "gujarati": "gu",
    "tamil": "ta",
    "telugu": "te",
    "kannada": "kn",
    "malayalam": "ml",
    "malyalam": "ml",
    "urdu": "ur",
    "spanish": "es",
    "french": "fr",
    "frech": "fr",
    "german": "de",
    "portuguese": "pt",
}

LANGUAGE_DISPLAY_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "te": "Telugu",
    "ta": "Tamil",
    "ml": "Malayalam",
    "kn": "Kannada",
}

SUPPORTED_PRIMARY_LANGUAGES = tuple(LANGUAGE_DISPLAY_NAMES.values())


@dataclass(frozen=True)
class LanguageContext:
    detected_code: str
    detected_language: str
    confidence: float
    target_language: str
    translation_enabled: bool
    style_instruction: str

    @property
    def prompt_instructions(self) -> str:
        instructions = [
            f"Detected user language: {self.detected_language} "
            f"(confidence {self.confidence:.2f}).",
            f"Response language: {self.target_language}.",
            f"Style: {self.style_instruction}",
        ]
        if self.translation_enabled:
            instructions.append(
                "Preserve technical terms, code, commands, file paths, and citations exactly."
            )
        return "\n".join(instructions)

    def trace(self) -> dict[str, Any]:
        return {
            "detected_code": self.detected_code,
            "detected_language": self.detected_language,
            "confidence": self.confidence,
            "target_language": self.target_language,
            "translation_enabled": self.translation_enabled,
            "style_instruction": self.style_instruction,
        }


def _script_matches(text: str) -> tuple[str, str, float] | None:
    total_letters = len(re.findall(r"\w", text or "", flags=re.UNICODE))
    if not total_letters:
        return None

    best = ("en", "English", 0.0)
    for code, (name, pattern) in SCRIPT_RANGES.items():
        count = len(re.findall(pattern, text or ""))
        confidence = count / max(total_letters, 1)
        if confidence > best[2]:
            best = (code, name, confidence)

    return best if best[2] >= 0.15 else None


def _latin_hint_matches(text: str) -> tuple[str, str, float] | None:
    words = re.findall(r"[a-zA-Z]+", (text or "").lower())
    if not words:
        return None

    best = ("en", "English", 0.0)
    word_set = set(words)
    for code, (name, hints) in LATIN_HINTS.items():
        hits = len(word_set.intersection(hints))
        confidence = hits / max(min(len(word_set), 8), 1)
        if confidence > best[2]:
            best = (code, name, confidence)

    return best if best[2] >= 0.2 else None


def detect_language(text: str, enabled: bool = True) -> tuple[str, str, float]:
    if not enabled:
        return "en", "English", 0.0

    script_match = _script_matches(text)
    if script_match:
        return script_match

    latin_match = _latin_hint_matches(text)
    if latin_match:
        return latin_match

    return "en", "English", 0.55


def build_language_context(text: str, settings: Any) -> LanguageContext:
    code, language, confidence = detect_language(
        text,
        enabled=getattr(settings, "language_detection_enabled", True),
    )
    translation_enabled = getattr(settings, "translation_enabled", False)
    configured_target = getattr(settings, "translation_target_language", "English")
    target_key = str(configured_target).strip().lower()
    style_code = LANGUAGE_NAME_TO_CODE.get(target_key, code)
    target_language = (
        LANGUAGE_DISPLAY_NAMES.get(style_code, str(configured_target).strip() or "English")
        if translation_enabled
        else language
    )
    style_instruction = STYLE_BY_CODE.get(style_code, STYLE_BY_CODE["en"])

    if translation_enabled:
        style_instruction = (
            f"{style_instruction} Translate the final answer from {language} into {target_language}."
        )

    return LanguageContext(
        detected_code=code,
        detected_language=language,
        confidence=round(confidence, 2),
        target_language=target_language,
        translation_enabled=translation_enabled,
        style_instruction=style_instruction,
    )
