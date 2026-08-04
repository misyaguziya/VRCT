from openai import OpenAI

try:
    from .translation_languages import translation_lang
    from .translation_utils import loadTranslatePromptConfig
    from .translation_openai import OpenAIClient, _authentication_check
except Exception:
    import sys
    from os import path as os_path
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_languages import translation_lang, loadTranslationLanguages
    from translation_utils import loadTranslatePromptConfig
    from translation_openai import OpenAIClient, _authentication_check
    translation_lang = loadTranslationLanguages(path=".", force=True)


# 除外対象のキーワード（互換エンドポイントでもテキスト翻訳に不適なモデルは弾く）
_EXCLUDE_KEYWORDS = [
    "whisper",
    "embedding",
    "image",
    "tts",
    "audio",
    "search",
    "transcribe",
    "diarize",
    "vision",
    "dall-e",
    "moderation",
    "rerank",
]


def _get_available_text_models(api_key: str, base_url: str) -> list[str]:
    """OpenAI 互換エンドポイント向け：除外条件に該当しないテキストモデルを全て許可する。

    プロバイダ独自命名（`llama-3.3-70b`, `mistral-large-latest`, `claude-3-5-sonnet` 等）
    が多いため `gpt-` プレフィックス判定は行わない。
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    res = client.models.list()
    allowed_models = []

    for m in res.data:
        model_id = m.id
        model_id_lower = model_id.lower()
        if any(kw in model_id_lower for kw in _EXCLUDE_KEYWORDS):
            continue
        allowed_models.append(model_id)

    allowed_models.sort()
    return allowed_models


class OpenAICompatibleClient(OpenAIClient):
    """OpenAI 互換エンドポイント向け翻訳クライアント。

    公式 `OpenAIClient` を継承し、以下 2 点だけを差し替える：
      - base_url を必須化し既定値を持たせる
      - モデルフィルタを緩め、プロバイダ独自命名を許容する
    """
    DEFAULT_BASE_URL = "https://api.openai.com/v1"

    def __init__(self, base_url: str | None = None, root_path: str = None):
        # OpenAIClient.__init__ を再実装：プロンプトファイルと supported_languages を差し替えるため
        self.api_key = None
        self.model = None
        self.base_url = base_url if base_url else self.DEFAULT_BASE_URL

        prompt_config = loadTranslatePromptConfig(root_path, "translation_openai_compatible.yml")
        self.supported_languages = list(translation_lang["OpenAI_Compatible"]["source"].keys())
        self.prompt_template = prompt_config["system_prompt"]
        self.history_cfg = prompt_config.get("history", {
            "use_history": False,
            "sources": [],
            "max_messages": 0,
            "max_chars": 0,
            "header_template": "",
            "item_template": "[{source}] {role}: {text}",
        })
        self._context_history: list[dict] = []
        self.openai_llm = None

    def getBaseURL(self) -> str:
        return self.base_url

    def setBaseURL(self, base_url: str) -> None:
        self.base_url = base_url if base_url else self.DEFAULT_BASE_URL

    def getModelList(self) -> list[str]:
        if not self.api_key or not self.base_url:
            return []
        try:
            return _get_available_text_models(self.api_key, self.base_url)
        except Exception:
            return []

    def setAuthKey(self, api_key: str) -> bool:
        # 認証は現在の base_url に対して行う
        result = _authentication_check(api_key, self.base_url)
        if result:
            self.api_key = api_key
        return result


if __name__ == "__main__":
    URL = input("OPENAI_COMPATIBLE_URL (blank=official): ").strip() or None
    KEY = input("AUTH_KEY: ")
    client = OpenAICompatibleClient(base_url=URL)
    client.setAuthKey(KEY)
    models = client.getModelList()
    if models:
        print("Available models:", models)
        m = input("Select a model: ")
        client.setModel(m)
        client.updateClient()
        print(client.translate("こんにちは世界", "Japanese", "English"))
