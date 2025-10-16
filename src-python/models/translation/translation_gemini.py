import logging
from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI
import yaml
from os import path as os_path

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

def _load_prompt_config(root_path: str = None) -> dict:
    """プロンプト設定をYAMLファイルから読み込む"""
    prompt_filename = "translation_gemini.yml"

    # PyInstallerでビルドされた場合のパス
    if root_path and os_path.exists(os_path.join(root_path, "_internal", "prompt", prompt_filename)):
        prompt_path = os_path.join(root_path, "_internal", "prompt", prompt_filename)
    # src-pythonフォルダから直接実行している場合のパス
    elif os_path.exists(os_path.join(os_path.dirname(__file__), "models", "translation", "prompt", prompt_filename)):
        prompt_path = os_path.join(os_path.dirname(__file__), "models", "translation", "prompt", prompt_filename)
    # translationフォルダから直接実行している場合のパス
    elif os_path.exists(os_path.join(os_path.dirname(__file__), "prompt", prompt_filename)):
        prompt_path = os_path.join(os_path.dirname(__file__), "prompt", prompt_filename)
    else:
        raise FileNotFoundError(f"Prompt file not found: {prompt_filename}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class GeminiClient:
    def __init__(self, root_path: str = None):
        self.api_key = None
        self.model = None

        # プロンプト設定をYAMLファイルから読み込む
        prompt_config = _load_prompt_config(root_path)
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