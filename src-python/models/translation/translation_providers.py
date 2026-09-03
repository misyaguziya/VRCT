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

対象エンジンは2つの形状に分かれる。無理に1つの形状へ押し込めるのではなく、
「実際に2つ以上の実装が同じ構造を持つか」を基準に別レジストリとして分けた。

    - `TRANSLATION_PROVIDER_REGISTRY` (認証キー + モデル一覧型、5エンジン):
      Plamo/Gemini/OpenAI/Groq/OpenRouter。controller.py 側は
      `Controller._getTranslationEngineAuthKey` 等の6メソッドに委譲する。
    - `CONNECTION_PROVIDER_REGISTRY` (疎通確認型、2エンジン): LMStudio/
      Ollama。認証キーを持たず、URL指定またはローカル自動検出で接続を
      確認する。controller.py 側は `Controller._checkTranslationEngineConnection`
      に委譲する。モデル一覧取得/選択モデル変更の3メソッドは
      `selectable_model_list_attr`/`selected_model_attr`/`error_model_invalid`
      という共通フィールド名を介して認証キー型と共有する
      (`Controller._resolveEngineSpec` 参照)。

以下は検討した上で、実際に重複する2つ目の実装が存在しない (＝抽象化しても
「新エンジン追加が楽になる」効果が無い) ため、あえて対象外とした:

    - `OpenAI_Compatible` は base_url 依存・入力の strip・認証成功の判定条件
      (モデル一覧が非空であること) の3点で「認証キー型」と異なり、かつ
      URL変更時に「認証成功後にURLを確定する」という、この1エンジンにしか
      無い順序制御を持つ。同じ形の2つ目のエンジンが無い一点物のため対象外。
    - `DeepL_API` はモデル一覧を持たないため対象外。
    - `Google`/`Bing`/`Papago` (無料Web翻訳) や `CTranslate2` (ローカル
      重み) は認証もモデル一覧もなく、この抽象化の対象外。

これらは将来、実際に同じ形のエンジンが2つ以上になった時点で改めて
レジストリ化を検討する。

段階移行の経緯: `TRANSLATION_PROVIDER_REGISTRY` はまず Gemini 1エンジンを
パイロットとして通し、既存の全テストが無変化で通ることを確認してから、
同じ形状の残り4エンジン (Plamo/OpenAI/Groq/OpenRouter) に一括展開した。
`CONNECTION_PROVIDER_REGISTRY` は最初から LMStudio/Ollama の2エンジンを
同時に載せている (この形状は最初から2実装が確認できていたため、
1エンジンだけのパイロット段階を挟む必要が無いと判断した)。
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


@dataclass(frozen=True)
class ConnectionEngineSpec:
    """認証キーを持たず、疎通確認 (URL指定 または ローカル自動検出) で
    モデル一覧を取得する翻訳エンジン1つ分のメタデータ。対象は
    `LMStudio`/`Ollama` の2エンジンのみ。

    `TranslationEngineSpec` (認証キー型) と異なり「接続呼び出し自体に
    渡す引数」がエンジンごとに違う (LMStudioはbase_url、Ollamaは引数なし)
    ため、その差異は呼び出し側 (controller.py の各薄い委譲メソッド) が
    `connect_kwargs` として都度組み立てて渡す — このスペック自体には
    含めない。

    `selectable_model_list_attr`/`selected_model_attr`/`error_model_invalid`
    は `TranslationEngineSpec` と同じ意味・同じフィールド名を持たせてあり、
    モデル一覧取得/選択モデル変更の3メソッド
    (`Controller._getTranslationEngineModelList` 等) は両スペックを
    区別せず共通で使う (`Controller._resolveEngineSpec` 参照)。
    """

    engine_key: str  # config.SELECTABLE_TRANSLATION_ENGINE_STATUS 等のキー
    error_connection_failed: ErrorCode  # 接続呼び出し失敗時に返すエラーコード
    error_model_invalid: ErrorCode  # setModel 失敗時に返すエラーコード
    selectable_model_list_attr: str  # config.SELECTABLE_X_MODEL_LIST の属性名
    selected_model_attr: str  # config.SELECTED_X_MODEL の属性名
    run_mapping_selectable_key: str  # mainloop.run_mapping の対応キー
    run_mapping_selected_key: str  # mainloop.run_mapping の対応キー


CONNECTION_PROVIDER_REGISTRY: Dict[str, ConnectionEngineSpec] = {
    "LMStudio": ConnectionEngineSpec(
        engine_key="LMStudio",
        error_connection_failed=ErrorCode.CONNECTION_LMSTUDIO_FAILED,
        error_model_invalid=ErrorCode.MODEL_LMSTUDIO_INVALID,
        selectable_model_list_attr="SELECTABLE_LMSTUDIO_MODEL_LIST",
        selected_model_attr="SELECTED_LMSTUDIO_MODEL",
        run_mapping_selectable_key="selectable_lmstudio_model_list",
        run_mapping_selected_key="selected_lmstudio_model",
    ),
    "Ollama": ConnectionEngineSpec(
        engine_key="Ollama",
        error_connection_failed=ErrorCode.CONNECTION_OLLAMA_FAILED,
        error_model_invalid=ErrorCode.MODEL_OLLAMA_INVALID,
        selectable_model_list_attr="SELECTABLE_OLLAMA_MODEL_LIST",
        selected_model_attr="SELECTED_OLLAMA_MODEL",
        run_mapping_selectable_key="selectable_ollama_model_list",
        run_mapping_selected_key="selected_ollama_model",
    ),
}
