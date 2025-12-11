import requests
from langchain_ollama import ChatOllama

try:
    from .translation_languages import translation_lang
    from .translation_utils import loadPromptConfig
except Exception:
    import sys
    from os import path as os_path
    sys.path.append(os_path.dirname(os_path.abspath(__file__)))
    from translation_languages import translation_lang, loadTranslationLanguages
    from translation_utils import loadPromptConfig
    translation_lang = loadTranslationLanguages(path=".", force=True)

def _authentication_check(base_url: str | None = None) -> bool:
    """Check authentication for Ollama API.
    """
    try:
        response = requests.get(f"{base_url}", timeout=0.2)
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception:
        return False

def _get_available_text_models(base_url: str | None = None) -> list[str]:
    """Extract available text models from Ollama.
    """
    try:
        response = requests.get(f"{base_url}/api/tags")
        models = response.json()["models"]
    except Exception:
        models = []

    allowed_models = []
    for model in models:
        allowed_models.append(model["name"])

    allowed_models.sort()
    return allowed_models

class OllamaClient:
    """Ollama Translation simple wrapper.
    prompt/translation_ollama.yml から system_prompt / supported_languages を読み込む。
    """
    def __init__(self, root_path: str = None):
        self.model = None
        self.base_url = "http://localhost:11434"

        prompt_config = loadPromptConfig(root_path, "translation_ollama.yml")
        self.supported_languages = list(translation_lang["Ollama"]["source"].keys())
        self.prompt_template = prompt_config["system_prompt"]

        self.openai_llm = None

    def authenticationCheck(self) -> bool:
        return _authentication_check(self.base_url)

    def getModelList(self) -> list[str]:
        if self.authenticationCheck():
            return _get_available_text_models(self.base_url)
        return []

    def getModel(self) -> str:
        return self.model

    def setModel(self, model: str) -> bool:
        if model in self.getModelList():
            self.model = model
            return True
        else:
            return False

    def updateClient(self) -> None:
        self.openai_llm = ChatOllama(
            base_url=self.base_url,
            model=self.model,
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
    client = OllamaClient()
    models = client.getModelList()
    if models:
        print("Available models:", models)
        model = input("Select a model: ")
        client.setModel(model)
        client.updateClient()
        print(client.translate("こんにちは世界", "Japanese", "English"))