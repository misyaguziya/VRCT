"""VRCTの言語設定を、RapidOCR(ONNX)で使うモデルの組み合わせへ変換する。

PP-OCRv6 small は1つのモデルに日本語・英語・中国語(簡繁)とラテン文字系40言語が
入っているので、この範囲は言語を選ばせずに読める。一方ハングル・キリル文字・タイ文字・
アラビア文字・デーヴァナーガリーは v6 small に含まれず、PP-OCRv5 のスクリプト別
モデルへ切り替える必要がある。そのため設定値は「自動」＋切り替えが必要な文字体系だけを
選択肢にしている。

実測 (学習用データセットの吹き出し95枚, CPU):
  v6 small : CER 0.27 / ほぼ正解 66%   ← 日英中+ラテンで最良
  v5 ch    : CER 0.62 / 54%
  EasyOCR  : CER 0.69 / 34%
  ハングル・キリル・タイは v5 のスクリプト別モデルでのみ読めた (CER 0.12 / 0.08 / 0.00)
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class OcrModelSpec:
    """RapidOCRに渡すモデルの指定。lang_rec=None はそのモデルの既定(多言語)を使う。"""

    ocr_version: str  # "PP-OCRv6" / "PP-OCRv5"
    model_type: str   # "small" / "mobile"
    lang_rec: Optional[str] = None

    @property
    def label(self) -> str:
        return f"{self.ocr_version}/{self.model_type}/{self.lang_rec or 'default'}"


# 日英中＋ラテン文字系。1モデルで読めるので言語を選ぶ必要がない。
AUTO = "auto"
_MULTILINGUAL = OcrModelSpec("PP-OCRv6", "small")

# 文字体系ごとに別モデルが要るものだけを選択肢にする。
_BY_LANGUAGE: Dict[str, OcrModelSpec] = {
    AUTO: _MULTILINGUAL,
    "Korean": OcrModelSpec("PP-OCRv5", "mobile", "korean"),
    "Russian": OcrModelSpec("PP-OCRv5", "mobile", "cyrillic"),
    "Ukrainian": OcrModelSpec("PP-OCRv5", "mobile", "cyrillic"),
    "Thai": OcrModelSpec("PP-OCRv5", "mobile", "th"),
    "Arabic": OcrModelSpec("PP-OCRv5", "mobile", "arabic"),
    "Hindi": OcrModelSpec("PP-OCRv5", "mobile", "devanagari"),
}

# v6 small が1モデルで読む言語。設定として受け付けるが、動作は auto と同じ。
# 以前のバージョンで個別の言語名を保存していた設定を、そのまま使えるようにするため。
_COVERED_BY_MULTILINGUAL = (
    "Japanese", "English", "Chinese Simplified", "Chinese Traditional",
    "French", "German", "Spanish", "Italian", "Portuguese", "Dutch",
    "Polish", "Turkish", "Vietnamese", "Indonesian",
)

# UIに出す選択肢。autoが先頭。
SELECTABLE_LANGUAGES: Tuple[str, ...] = (AUTO,) + tuple(
    sorted(k for k in _BY_LANGUAGE if k != AUTO))


def isSupported(vrct_language: str) -> bool:
    return resolveModelSpec(vrct_language) is not None


def resolveModelSpec(vrct_language: str) -> Optional[OcrModelSpec]:
    """設定値から使用するモデルを決める。未対応・未設定は None。"""
    if not isinstance(vrct_language, str) or not vrct_language:
        return None
    spec = _BY_LANGUAGE.get(vrct_language)
    if spec is not None:
        return spec
    if vrct_language in _COVERED_BY_MULTILINGUAL:
        return _MULTILINGUAL
    return None
