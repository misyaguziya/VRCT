"""翻訳エンジンをプラガブルにするためのレジストリ抽象化。

バックエンドレビュー (`docs/backend_review_2026-08-27.md`) フェーズ3・
項目17: 「認証キー + モデル一覧」型の翻訳エンジン
(Plamo/Gemini/OpenAI/Groq/OpenRouter) は現状、以下の4層に
ほぼ一字一句同じコードがエンジンの数だけ並んでいる。

    1. `translation_translator.py` (`Translator` ファサード) の
       `authenticationX` / `getXModelList` / `setXModel` / `updateXClient`
    2. `model.py` の委譲ラッパー (`authenticationTranslatorXAuthKey` 等)
    3. `controller.py` の CRUD エンドポイント
       (`get/set/delXAuthKey`, `getXModelList`, `get/setXModel`)
    4. `config.py` の `SELECTABLE_X_MODEL_LIST` / `SELECTED_X_MODEL`
       ディスクリプタ + `mainloop.py` のルーティングテーブル

このモジュールは「エンジンごとに何が違うか」だけをデータとして
`TRANSLATION_PROVIDER_REGISTRY` に集約し、新しいエンジンを足すコストを
「8箇所編集」から「レジストリに1エントリ追加」に近づけることを狙う。

文字起こし側の `TranscriptionProvider`
(`models/transcription/transcription_providers.py`) と対になる設計だが
役割は異なる: あちらは「1回の書き起こし呼び出し」を差し替え可能にする
*ランタイム*抽象化。こちらは翻訳エンジンのクライアントクラス
(`GeminiClient` 等) が `translate()` を含めて既に完全に同一の
インターフェースを持っているため、ランタイム側の抽象化は不要で、
「認証・モデル管理の CRUD」を差し替え可能にする*管理面*の抽象化として
機能する。

対象は現時点で「認証キー + モデル一覧」型の5エンジンのみ:

    - `OpenAI_Compatible` は base_url に依存し、かつ認証成功の判定条件
      (モデル一覧が非空であること) が他の5エンジンと異なるため対象外。
    - `LMStudio`/`Ollama` は認証キー自体を持たない (base_url またはローカル
      検出) ため対象外。
    - `DeepL_API` はモデル一覧を持たないため対象外。
    - `Google`/`Bing`/`Papago` (無料Web翻訳) や `CTranslate2` (ローカル
      重み) は認証もモデル一覧もなく、この抽象化の対象外。

これらは将来、必要になった時点で別のレジストリ形状として追加を検討する
(無理に1つの形状に押し込めない)。

段階移行の計画: このコミット時点では、このレジストリは
controller.py / model.py / translation_translator.py の**どこからも
参照されていない** (設計のみ、挙動変化なし)。次段階でまず Gemini
1エンジンだけをこのレジストリ経由の実装に置き換え、既存の全テストが
無変化で通ることを確認してから、同じ形状の残り4エンジンに一括展開する。
"""

from dataclasses import dataclass
from typing import Callable, Dict, Type

from errors import ErrorCode

try:
    from .translation_gemini import GeminiClient
    from .translation_groq import GroqClient
    from .translation_openai import OpenAIClient
    from .translation_openrouter import OpenRouterClient
    from .translation_plamo import PlamoClient
except Exception:
    from translation_gemini import GeminiClient
    from translation_groq import GroqClient
    from translation_openai import OpenAIClient
    from translation_openrouter import OpenRouterClient
    from translation_plamo import PlamoClient


# クライアントクラスがこの形状の一員であるために必須のメソッド。
# レジストリの自己整合性テスト (test_translation_providers.py) で
# 全登録クライアントがこれを満たすことを検証する。
REQUIRED_CLIENT_METHODS = (
    "getModelList",
    "getAuthKey",
    "setAuthKey",
    "getModel",
    "setModel",
    "updateClient",
    "translate",
)


def _validate_min_length(min_length: int) -> Callable[[str], bool]:
    """キー長のみで一次検証するエンジン向け (Plamo/Gemini/OpenRouter)。"""
    return lambda data: len(data) >= min_length


def _validate_prefix_and_min_length(prefix: str, min_length: int) -> Callable[[str], bool]:
    """プレフィックス+キー長で一次検証するエンジン向け (OpenAI/Groq)。"""
    return lambda data: data.startswith(prefix) and len(data) >= min_length


@dataclass(frozen=True)
class TranslationEngineSpec:
    """「認証キー + モデル一覧」型の翻訳エンジン1つ分のメタデータ。"""

    engine_key: str  # config.AUTH_KEYS のキー (例: "Gemini_API")
    client_class: Type  # models.translation.translation_X.XClient
    auth_validate: Callable[[str], bool]  # 実際の認証呼び出し前のフォーマット検証
    error_auth_invalid: ErrorCode  # フォーマット検証失敗時に返すエラーコード
    error_auth_failed: ErrorCode  # 実際の認証 (API呼び出し) 失敗時に返すエラーコード
    error_model_invalid: ErrorCode  # setModel 失敗時に返すエラーコード
    selectable_model_list_attr: str  # config.SELECTABLE_X_MODEL_LIST の属性名
    selected_model_attr: str  # config.SELECTED_X_MODEL の属性名
    run_mapping_selectable_key: str  # mainloop.run_mapping の対応キー ("selectable_x_model_list")
    run_mapping_selected_key: str  # mainloop.run_mapping の対応キー ("selected_x_model")


TRANSLATION_PROVIDER_REGISTRY: Dict[str, TranslationEngineSpec] = {
    "Plamo_API": TranslationEngineSpec(
        engine_key="Plamo_API",
        client_class=PlamoClient,
        auth_validate=_validate_min_length(72),
        error_auth_invalid=ErrorCode.AUTH_PLAMO_LENGTH,
        error_auth_failed=ErrorCode.AUTH_PLAMO_FAILED,
        error_model_invalid=ErrorCode.MODEL_PLAMO_INVALID,
        selectable_model_list_attr="SELECTABLE_PLAMO_MODEL_LIST",
        selected_model_attr="SELECTED_PLAMO_MODEL",
        run_mapping_selectable_key="selectable_plamo_model_list",
        run_mapping_selected_key="selected_plamo_model",
    ),
    "Gemini_API": TranslationEngineSpec(
        engine_key="Gemini_API",
        client_class=GeminiClient,
        auth_validate=_validate_min_length(39),
        error_auth_invalid=ErrorCode.AUTH_GEMINI_LENGTH,
        error_auth_failed=ErrorCode.AUTH_GEMINI_FAILED,
        error_model_invalid=ErrorCode.MODEL_GEMINI_INVALID,
        selectable_model_list_attr="SELECTABLE_GEMINI_MODEL_LIST",
        selected_model_attr="SELECTED_GEMINI_MODEL",
        run_mapping_selectable_key="selectable_gemini_model_list",
        run_mapping_selected_key="selected_gemini_model",
    ),
    "OpenAI_API": TranslationEngineSpec(
        engine_key="OpenAI_API",
        client_class=OpenAIClient,
        auth_validate=_validate_prefix_and_min_length("sk-", 164),
        error_auth_invalid=ErrorCode.AUTH_OPENAI_INVALID,
        error_auth_failed=ErrorCode.AUTH_OPENAI_FAILED,
        error_model_invalid=ErrorCode.MODEL_OPENAI_INVALID,
        selectable_model_list_attr="SELECTABLE_OPENAI_MODEL_LIST",
        selected_model_attr="SELECTED_OPENAI_MODEL",
        run_mapping_selectable_key="selectable_openai_model_list",
        run_mapping_selected_key="selected_openai_model",
    ),
    "Groq_API": TranslationEngineSpec(
        engine_key="Groq_API",
        client_class=GroqClient,
        auth_validate=_validate_prefix_and_min_length("gsk", 40),
        error_auth_invalid=ErrorCode.AUTH_GROQ_INVALID,
        error_auth_failed=ErrorCode.AUTH_GROQ_FAILED,
        error_model_invalid=ErrorCode.MODEL_GROQ_INVALID,
        selectable_model_list_attr="SELECTABLE_GROQ_MODEL_LIST",
        selected_model_attr="SELECTED_GROQ_MODEL",
        run_mapping_selectable_key="selectable_groq_model_list",
        run_mapping_selected_key="selected_groq_model",
    ),
    "OpenRouter_API": TranslationEngineSpec(
        engine_key="OpenRouter_API",
        client_class=OpenRouterClient,
        auth_validate=_validate_min_length(20),
        # NOTE: 実装は長さのみの検証だが、既存のエラーコード名は
        # (Plamo/Gemini の "_LENGTH" ではなく) "_INVALID"。既存の
        # フロントエンド契約を変えないため、命名の不整合はそのまま踏襲する。
        error_auth_invalid=ErrorCode.AUTH_OPENROUTER_INVALID,
        error_auth_failed=ErrorCode.AUTH_OPENROUTER_FAILED,
        error_model_invalid=ErrorCode.MODEL_OPENROUTER_INVALID,
        selectable_model_list_attr="SELECTABLE_OPENROUTER_MODEL_LIST",
        selected_model_attr="SELECTED_OPENROUTER_MODEL",
        run_mapping_selectable_key="selectable_openrouter_model_list",
        run_mapping_selected_key="selected_openrouter_model",
    ),
}
