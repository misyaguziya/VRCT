"""Mapping between VRCT language names and EasyOCR language codes.

EasyOCRのReaderは1つのスクリプトグループしか同時にロードできない。
ja / ko / ch_sim / ch_tra / th / ta / te / kn はそれぞれ英語としか併用できず
(easyocr側が 'X is only compatible with English' で弾く)、ラテン文字系の
言語同士は併用できる。つまり「1つのReaderでどの言語でも読む」は作れないため、
読み取る言語はユーザーに明示的に選ばせる (autoは廃止)。
"""

from typing import List, Optional, Tuple

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

# UIの選択肢。VRCTが扱う言語の全てをOCRできるわけではないので、
# ここに載っているものだけを選ばせる。
SUPPORTED_LANGUAGES: Tuple[str, ...] = tuple(sorted(_VRCT_TO_EASYOCR))


def isSupported(vrct_language: str) -> bool:
    return isinstance(vrct_language, str) and vrct_language in _VRCT_TO_EASYOCR


def vrctToEasyocr(vrct_language: str) -> Optional[str]:
    """Return the EasyOCR code for a VRCT language name, or None if unsupported."""
    if not isinstance(vrct_language, str):
        return None
    return _VRCT_TO_EASYOCR.get(vrct_language)


def resolveEasyocrLangs(source_language: str) -> List[str]:
    """Return the EasyOCR language codes to load, or [] if the language is unusable.

    英語以外は 'en' を足して、同じ吹き出しに混ざるラテン文字も読めるようにする
    (EasyOCRはどのグループでも英語との併用は許している)。
    未対応・未選択は空リストを返し、呼び出し側が起動を拒否する。
    """
    code = vrctToEasyocr(source_language)
    if code is None:
        return []
    if code == "en":
        return ["en"]
    return [code, "en"]
