import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger("langchain_google_genai")
logger.setLevel(logging.ERROR)

_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite", # default
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash-8b"
    "gemini-1.5-flash",
    ]

class GeminiClient:
    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash-lite"):
        self.api_key = api_key
        self.model = model
        self.prompt_template = """
        Please translate the following text from {input_lang} to {output_lang}.
        Only provide the translated text as the output.
        {text}
        """
        self.gemini_llm = ChatGoogleGenerativeAI(
            model=self.model,
            api_key=self.api_key,
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
            self.gemini_llm = ChatGoogleGenerativeAI(
                model=self.model,
                api_key=self.api_key,
            )
            return True
        except Exception as e:
            print(f"Error setting AuthKey: {e}")
            return False

    def setModel(self, model: str) -> bool:
        """モデルを設定し、成功したかどうかを返す"""
        try:
            if model in _MODELS:
                self.model = model
                self.gemini_llm = ChatGoogleGenerativeAI(
                    model=self.model,
                    api_key=self.api_key,
                )
                return True
            else:
                print(f"Model {model} is not supported.")
                return False
        except Exception as e:
            print(f"Error setting model: {e}")
            return False

    def translate(self, text: str, input_lang: str, output_lang: str) -> str:
        messages = self.prompt_template.format(
                    input_lang=input_lang,
                    output_lang=output_lang,
                    text=text
                )

        output = self.gemini_llm.invoke([HumanMessage(content=messages)])
        return output.content

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

    gemini_client = GeminiClient(api_key=AUTH_KEY, model="gemini-2.5-flash-lite")

    print("model list:", gemini_client.getListModels())
    print("AuthKey:", gemini_client.getAuthKey())
    # print("Model:", gemini_client.getModel())
    # print(f"set model: {gemini_client.setModel('gemini-2.5-flash')}")
    # print(f"set AuthKey: {gemini_client.setAuthKey(AUTH_KEY)}")
    # print(f"check AuthKey: {gemini_client.checkAuthKey()}")

    # try:
    #     translated_text = gemini_client.translate(text, input_lang, output_lang)
    #     print(translated_text)
    # except Exception:
    #     print("Invalid API key. Please check your credentials.")


    supported_languages = """
    Arabic
    Bengali
    Bulgarian
    Simplified Chinese
    Traditional Chinese
    Croatian
    Czech
    Danish
    Dutch
    English
    Estonian
    Finnish
    French
    German
    Greek
    Hebrew
    Hindi
    Hungarian
    Indonesian
    Italian
    Japanese
    Korean
    Latvian
    Lithuanian
    Norwegian
    Polish
    Portuguese
    Romanian
    Russian
    Serbian
    Slovak
    Slovenian
    Spanish
    Swahili
    Swedish
    Thai
    Turkish
    Ukrainian
    Vietnamese
    """

    for lang in supported_languages.split("\n"):
        if lang == "":
            continue
        print (f"Translating to {lang}:")
        try:
            translated_text = gemini_client.translate(text, input_lang, lang)
            print(f"Translated text: {translated_text}")
        except Exception as e:
            print(f"Error translating to {lang} api limit")
            print(f"Error reason: {e}")
            break