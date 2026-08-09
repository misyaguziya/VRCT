"""Mapping between VRCT language names and EasyOCR language codes."""

from typing import List

# VRCT language name -> EasyOCR ISO code
_VRCT_TO_EASYOCR = {
    "Japanese": "ja",
    "English": "en",
    "Korean": "ko",
    "Chinese Simplified": "ch_sim",
    "Chinese Traditional": "ch_tra",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Dutch": "nl",
    "Polish": "pl",
    "Turkish": "tr",
    "Vietnamese": "vi",
    "Thai": "th",
    "Indonesian": "id",
    "Arabic": "ar",
    "Hindi": "hi",
    "Ukrainian": "uk",
}

# Default fallback set (JP + EN covers most VRChat traffic).
_DEFAULT_LANGS = ["ja", "en"]


def vrctToEasyocr(vrct_language: str) -> str:
    """Return the EasyOCR code for a VRCT language name, or 'en' if unknown."""
    return _VRCT_TO_EASYOCR.get(vrct_language, "en")


def resolveEasyocrLangs(source_language: str) -> List[str]:
    """Return the list of EasyOCR language codes to load for a given source.

    'auto' loads a JP+EN combo which covers the common VRChat use case.
    Any known VRCT language name returns [that_code, 'en'] so Latin fallback
    is available for mixed-language bubbles. Any unknown value falls back
    to the JP+EN default set.
    """
    if not isinstance(source_language, str) or source_language.lower() == "auto":
        return list(_DEFAULT_LANGS)
    code = _VRCT_TO_EASYOCR.get(source_language)
    if code is None:
        return list(_DEFAULT_LANGS)
    if code == "en":
        return ["en"]
    return [code, "en"]
