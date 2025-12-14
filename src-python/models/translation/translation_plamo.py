from openai import OpenAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

try:
    from .translation_languages import translation_lang
    from .translation_utils import loadTranslatePromptConfig
except Exception:
    import sys
    from os import path as os_path
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_languages import translation_lang, loadTranslationLanguages
    from translation_utils import loadTranslatePromptConfig
    translation_lang = loadTranslationLanguages(path=".", force=True)

BASE_URL = "https://api.platform.preferredai.jp/v1"

def _authentication_check(api_key: str) -> bool:
    """Check if the provided API key is valid by attempting to list models.
    """
    try:
        client = OpenAI(api_key=api_key, base_url=BASE_URL)
        client.models.list()
        return True
    except Exception:
        return False

def _get_available_text_models(api_key: str) -> list[str]:
    """Extract all available models from the PLAMO API
    """
    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    res = client.models.list()
    allowed_models = []

    for model in res.data:
        allowed_models.append(model.id)

    allowed_models.sort()
    return allowed_models

class PlamoClient:
    def __init__(self, root_path: str = None):
        self.api_key = None
        self.base_url = BASE_URL
        self.model = None

        prompt_config = loadTranslatePromptConfig(root_path, "translation_plamo.yml")
        self.supported_languages = list(translation_lang["Plamo_API"]["source"].keys())
        self.prompt_template = prompt_config["system_prompt"]

        self.plamo_llm = None

    def getModelList(self) -> list[str]:
        return _get_available_text_models(self.api_key) if self.api_key else []

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
        self.plamo_llm = ChatOpenAI(
            base_url=self.base_url,
            model=self.model,
            streaming=False,
            api_key=SecretStr(self.api_key),
        )

    def translate(self, text: str, input_lang: str, output_lang: str) -> str:
        system_prompt = self.prompt_template.format(
            supported_languages=self.supported_languages,
            input_lang=input_lang,
            output_lang=output_lang
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        resp = self.plamo_llm.invoke(messages)
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
    AUTH_KEY = "PLAMO_API_KEY"
    client = PlamoClient()
    client.setAuthKey(AUTH_KEY)
    models = client.getModelList()
    if models:
        print("Available models:", models)
        model = input("Select a model: ")
        client.setModel(model)
        client.updateClient()
        print(client.translate("こんにちは世界", "Japanese", "English"))