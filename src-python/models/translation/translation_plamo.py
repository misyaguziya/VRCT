from langchain_openai import ChatOpenAI
from pydantic import SecretStr

_MODELS = [
    "plamo-2.0-prime"
    ]

class PlamoClient:
    def __init__(self, api_key: str = "", model: str = "plamo-2.0-prime"):
        self.api_key = api_key
        self.base_url = "https://api.platform.preferredai.jp/v1"
        self.model = model
        self.supported_languages = """
        English
        Japanese
        Korean
        French
        German
        Spanish
        Portuguese
        Russian
        Italian
        Dutch
        Polish
        Turkish
        Arabic
        Hindi
        Thai
        Vietnamese
        Indonesian
        Malay
        Filipino
        Swedish
        Finnish
        Danish
        Norwegian
        Romanian
        Czech
        Hungarian
        Greek
        Hebrew
        Simplified Chinese
        Traditional Chinese
        """
        self.prompt_template = f"""
        You are a translation assistant that uses the `plamo-translate` tool.
        Translate the following text.Supported languages include:{self.supported_languages}
        Translate the following text from {{input_lang}} to {{output_lang}}.
        output only the translated text without any additional commentary.
        """
        self.plamo_llm = ChatOpenAI(
            base_url=self.base_url,
            model=self.model,
            streaming=True,
            api_key=SecretStr(self.api_key),
        )

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
            print(f"Error setting AuthKey: {e}")
            return False

    def setModel(self, model: str) -> bool:
        """モデルを設定し、成功したかどうかを返す"""
        if model not in _MODELS:
            print(f"Model {model} is not in the supported model list.")
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
                    input_lang=input_lang, output_lang=output_lang
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
        except Exception:
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