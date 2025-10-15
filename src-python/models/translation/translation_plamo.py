from langchain_openai import ChatOpenAI
from pydantic import SecretStr
import yaml
from os import path as os_path

_MODELS = [
    "plamo-2.0-prime"
    ]

class PlamoClient:
    def __init__(self, api_key: str = "", model: str = "plamo-2.0-prime", root_path: str = None):
        self.api_key = api_key
        self.base_url = "https://api.platform.preferredai.jp/v1"
        self.model = model

        # プロンプト設定をYAMLファイルから読み込む
        prompt_config = self._load_prompt_config(root_path)
        self.supported_languages = prompt_config["supported_languages"]
        self.prompt_template = prompt_config["system_prompt"]

        self.plamo_llm = ChatOpenAI(
            base_url=self.base_url,
            model=self.model,
            streaming=True,
            api_key=SecretStr(self.api_key),
        )

    def _load_prompt_config(self, root_path: str = None) -> dict:
        """プロンプト設定をYAMLファイルから読み込む"""
        prompt_filename = "translation_plamo.yml"

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

    def getListModels(self) -> list[str]:
        return _MODELS

    def getAuthKey(self) -> str:
        """現在のAuthKeyを取得する"""
        return self.api_key

    def getModel(self) -> str:
        """現在のモデルを取得する"""
        return self.model

    def setAuthKey(self, api_key: str) -> bool:
        """AuthKeyを設定し、成功したかどうかを返す"""
        try:
            self.api_key = api_key
            self.plamo_llm = ChatOpenAI(
                base_url=self.base_url,
                model=self.model,
                streaming=True,
                api_key=SecretStr(self.api_key),
            )
            return True
        except Exception as e:
            return False

    def setModel(self, model: str) -> bool:
        """モデルを設定し、成功したかどうかを返す"""
        if model not in _MODELS:
            return False

        try:
            self.model = model
            self.plamo_llm = ChatOpenAI(
                base_url=self.base_url,
                model=self.model,
                streaming=True,
                api_key=SecretStr(self.api_key),
            )
            return True
        except Exception as e:
            print(f"Error setting model: {e}")
            return False

    def translate(self, text: str, input_lang: str, output_lang: str) -> str:
        messages = [
            {
                "role": "system",
                "content": self.prompt_template.format(
                    supported_languages=self.supported_languages,
                    input_lang=input_lang,
                    output_lang=output_lang
                ),
            },
            {"role": "user", "content": text},
        ]

        output = ""
        for chunk in self.plamo_llm.stream(messages):
            if isinstance(chunk.content, str):
                output += chunk.content
            elif isinstance(chunk.content, list):
                for item in chunk.content:
                    if isinstance(item, str):
                        output += item
                    elif isinstance(item, dict):
                        if "content" in item and isinstance(item["content"], str):
                            output += item["content"]

        return output[:-1]

    def checkAuthKey(self) -> bool:
        try:
            self.setModel(self.model)
            self.translate("Hello World", input_lang="English", output_lang="Japanese")
            return True
        except Exception as e:
            print(f"Error checking AuthKey: {e}")
            return False

if __name__ == "__main__":
    AUTH_KEY = "AUTH_KEY"
    text = """
        毎朝コーヒーを入れるのがささやかな楽しみになってる
        """
    input_lang = "Japanese"
    output_lang = "English"

    plamo_client = PlamoClient(api_key=AUTH_KEY)

    print("model list:", plamo_client.getListModels())
    print("AuthKey:", plamo_client.getAuthKey())
    print("Model:", plamo_client.getModel())
    print(f"set model: {plamo_client.setModel('plamo-2.0-prime')}")
    print(f"set AuthKey: {plamo_client.setAuthKey(AUTH_KEY)}")
    print(f"check AuthKey: {plamo_client.checkAuthKey()}")

    try:
        translated_text = plamo_client.translate(text, input_lang, output_lang)
        print(translated_text)
    except Exception:
        print("Invalid API key. Please check your credentials.")