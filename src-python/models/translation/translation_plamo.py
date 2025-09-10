from langchain_openai import ChatOpenAI

class PlamoClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.platform.preferredai.jp/v1"
        self.model = "plamo-2.0-prime"
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
            openai_api_key=self.api_key,
        )

    def translate_text(self, text: str, input_lang: str, output_lang: str):
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
            output += chunk.content

        return output[:-1]


if __name__ == "__main__":
    text = """
        毎朝コーヒーを入れるのがささやかな楽しみになってる
        """
    input_lang = "Japanese"
    output_lang = "English"

    plamo_client = PlamoClient(api_key="AUTH_KEY")
    translated_text = plamo_client.translate_text(text, input_lang, output_lang)
    print(translated_text)