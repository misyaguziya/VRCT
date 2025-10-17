from openai import OpenAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
import yaml
from os import path as os_path

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
    """Extract the list of available text models from the LM Studio.
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    res = client.models.list()
    allowed_models = []

    for model in res.data:
        allowed_models.append(model.id)

    allowed_models.sort()
    return allowed_models

def _load_prompt_config(root_path: str = None) -> dict:
    prompt_filename = "translation_lmstudio.yml"
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

class LMStudioClient:
    """LM Studio Translation simple wrapper.
    prompt/translation_lmstudio.yml から system_prompt / supported_languages を読み込む。
    """
    def __init__(self, base_url: str | None = None, root_path: str = None):
        self.api_key = "lmstudio"
        self.model = None
        self.base_url = base_url  # None の場合は公式エンドポイント

        prompt_config = _load_prompt_config(root_path)
        self.supported_languages = prompt_config["supported_languages"]
        self.prompt_template = prompt_config["system_prompt"]

        self.openai_llm = None

    def getBaseURL(self) -> str | None:
        return self.base_url

    def setBaseURL(self, base_url: str | None) -> None:
        result = _authentication_check(api_key=self.api_key, base_url=base_url)
        if result:
            self.base_url = base_url
        return result

    def getModelList(self) -> list[str]:
        return _get_available_text_models(api_key=self.api_key, base_url=self.base_url) if self.base_url else []

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
    AUTH_KEY = "lm-studio"
    client = LMStudioClient(base_url="http://192.168.68.110:1234/v1")
    models = client.getModelList()
    print(models)
    # if models:
    # print("Available models:", models)
    # model = input("Select a model: ")
    client.setModel("google/gemma-3n-e4b")
    client.updateClient()
    print(client.translate("こんにちは世界", "Japanese", "English"))