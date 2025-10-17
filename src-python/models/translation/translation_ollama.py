import requests
from langchain_ollama import ChatOllama
import yaml
from os import path as os_path


def _authentication_check(base_url: str | None = None) -> bool:
    """Check authentication for Ollama API.
    """
    try:
        response = requests.get(f"{base_url}/api/ping")
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception:
        return False

def _get_available_text_models(base_url: str | None = None) -> list[str]:
    """Extract available text models from Ollama.
    """
    response = requests.get(f"{base_url}/api/tags")
    models = response.json()["models"]

    allowed_models = []
    for model in models:
        allowed_models.append(model["name"])

    allowed_models.sort()
    return allowed_models

def _load_prompt_config(root_path: str = None) -> dict:
    prompt_filename = "translation_ollama.yml"
    # PyInstaller 展開後
    if root_path and os_path.exists(os_path.join(root_path, "_internal", "prompt", prompt_filename)):
        prompt_path = os_path.join(root_path, "_internal", "prompt", prompt_filename)
    # src-python 直下実行
    elif os_path.exists(os_path.join(os_path.dirname(__file__), "models", "translation", "prompt", prompt_filename)):
        prompt_path = os_path.join(os_path.dirname(__file__), "models", "translation", "prompt", prompt_filename)
    # translation フォルダ直下実行
    elif os_path.exists(os_path.join(os_path.dirname(__file__), "prompt", prompt_filename)):
        prompt_path = os_path.join(os_path.dirname(__file__), "prompt", prompt_filename)
    else:
        raise FileNotFoundError(f"Prompt file not found: {prompt_filename}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class OllamaClient:
    """Ollama Translation simple wrapper.
    prompt/translation_ollama.yml から system_prompt / supported_languages を読み込む。
    """
    def __init__(self, root_path: str = None):
        self.model = None
        self.base_url = "http://localhost:11434"

        prompt_config = _load_prompt_config(root_path)
        self.supported_languages = prompt_config["supported_languages"]
        self.prompt_template = prompt_config["system_prompt"]

        self.openai_llm = None

    def getModelList(self) -> list[str]:
        if _authentication_check(self.base_url):
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