from openai import OpenAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

try:
    from .translation_languages import translation_lang
    from .translation_utils import loadPromptConfig
except Exception:
    import sys
    from os import path as os_path
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_languages import translation_lang, loadTranslationLanguages
    from translation_utils import loadPromptConfig
    translation_lang = loadTranslationLanguages(path=".", force=True)

def _authentication_check(api_key: str, base_url: str | None = None) -> bool:
    """Check if the provided API key is valid by attempting to list models.
    """
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        client.models.list()
        return True
    except Exception:
        return False

def _get_available_text_models(api_key: str, base_url: str | None = None) -> list[str]:
    """Extract only GPT models suitable for translation and chat applications (plus those with fine-tuning)
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    res = client.models.list()
    allowed_models = []

    for model in res.data:
        model_id = model.id
        root = getattr(model, "root", "")

        # 除外対象のキーワード
        exclude_keywords = [
            "whisper",       # 音声認識
            "embedding",     # 埋め込み
            "image",         # 画像生成
            "tts",           # 音声合成
            "audio",         # 音声系（transcribe, diarize含む）
            "search",        # 検索補助モデル
            "transcribe",    # 音声→文字起こし
            "diarize",       # 話者分離
            "vision"         # 画像入力系（旧gpt-4-visionなど）
        ]

        # 除外キーワードが含まれているモデルをスキップ
        if any(kw in model_id for kw in exclude_keywords):
            continue

        # GPTモデルまたはFine-tune GPTモデルのみ対象
        if model_id.startswith("gpt-"):
            allowed_models.append(model_id)
        elif model_id.startswith("ft:") and root.startswith("gpt-"):
            allowed_models.append(model_id)

    allowed_models.sort()
    return allowed_models

class OpenAIClient:
    """OpenAI Translation simple wrapper.
    prompt/translation_openai.yml から system_prompt / supported_languages を読み込む。
    """
    def __init__(self, base_url: str | None = None, root_path: str = None):
        self.api_key = None
        self.model = None
        self.base_url = base_url  # None の場合は公式エンドポイント

        prompt_config = loadPromptConfig(root_path, "translation_openai.yml")
        self.supported_languages = list(translation_lang["OpenAI_API"]["source"].keys())
        self.prompt_template = prompt_config["system_prompt"]

        self.openai_llm = None

    def getModelList(self) -> list[str]:
        return _get_available_text_models(self.api_key, self.base_url) if self.api_key else []

    def getAuthKey(self) -> str:
        return self.api_key

    def setAuthKey(self, api_key: str) -> bool:
        result = _authentication_check(api_key, self.base_url)
        if result:
            self.api_key = api_key
        return result

    def getModel(self) -> str:
        return self.model

    def setModel(self, model: str) -> bool:
        if model in self.getModelList():
            self.model = model
            return True
        else:
            return False

    def updateClient(self) -> None:
        self.openai_llm = ChatOpenAI(
            base_url=self.base_url,
            model=self.model,
            api_key=SecretStr(self.api_key),
            streaming=False,
        )

    def translate(self, text: str, input_lang: str, output_lang: str) -> str:
        system_prompt = self.prompt_template.format(
            supported_languages=self.supported_languages,
            input_lang=input_lang,
            output_lang=output_lang,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        resp = self.openai_llm.invoke(messages)
        content = ""
        if isinstance(resp.content, str):
            content = resp.content
        elif isinstance(resp.content, list):
            for part in resp.content:
                if isinstance(part, str):
                    content += part
                elif isinstance(part, dict) and "content" in part and isinstance(part["content"], str):
                    content += part["content"]
        return content.strip()

if __name__ == "__main__":
    AUTH_KEY = "OPENAI_API_KEY"
    client = OpenAIClient()
    client.setAuthKey(AUTH_KEY)
    models = client.getModelList()
    if models:
        print("Available models:", models)
        model = input("Select a model: ")
        client.setModel(model)
        client.updateClient()
        print(client.translate("こんにちは世界", "Japanese", "English"))