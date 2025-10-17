import logging
from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from .translation_utils import loadPromptConfig
except Exception:
    import sys
    from os import path as os_path
    print(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_utils import loadPromptConfig

logger = logging.getLogger("langchain_google_genai")
logger.setLevel(logging.ERROR)

def _authentication_check(api_key: str) -> bool:
    """Check if the provided API key is valid by attempting to list models.
    """
    try:
        client = genai.Client(api_key=api_key)
        client.models.list()
        return True
    except Exception:
        return False

def _get_available_text_models(api_key: str) -> list[str]:
    """Extract only Gemini models suitable for translation and chat applications
    """
    client = genai.Client(api_key=api_key)
    res = client.models.list()
    allowed_models = []

    # 除外対象のキーワード
    exclude_keywords = [
        "audio",
        "image",
        "veo",
        "tts",
        "robotics",
        "computer-use"
    ]
    for model in res:
        model_id = model.name
        if ("gemini" in model_id.lower() or "gemma" in model_id.lower()) and "generateContent" in model.supported_actions:
            if any(x in model_id for x in exclude_keywords):
                continue
            allowed_models.append(model_id.replace("models/", ""))
    allowed_models.sort()
    return allowed_models

class GeminiClient:
    def __init__(self, root_path: str = None):
        self.api_key = None
        self.model = None

        # プロンプト設定をYAMLファイルから読み込む
        prompt_config = loadPromptConfig(root_path, "translation_gemini.yml")
        self.supported_languages = prompt_config["supported_languages"]
        self.prompt_template = prompt_config["system_prompt"]

        self.gemini_llm = None

    def getModelList(self) -> list[str]:
        return _get_available_text_models(self.api_key)

    def getAuthKey(self) -> str:
        return self.api_key

    def setAuthKey(self, api_key: str) -> bool:
        result = _authentication_check(api_key)
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
        self.gemini_llm = ChatGoogleGenerativeAI(
            model=self.model,
            api_key=self.api_key,
        )

    def translate(self, text: str, input_lang: str, output_lang: str) -> str:
        system_prompt = self.prompt_template.format(
            supported_languages=self.supported_languages,
            input_lang=input_lang,
            output_lang=output_lang
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        resp = self.gemini_llm.invoke(messages)
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
    AUTH_KEY = "AUTH_KEY"
    client = GeminiClient()
    client.setAuthKey(AUTH_KEY)
    models = client.getModelList()
    if models:
        print("Available models:", models)
        model = input("Select a model: ")
        client.setModel(model)
        client.updateClient()
        print(client.translate("こんにちは世界", "Japanese", "English"))