from deepl import Translator as deepl_Translator
from deepl_translate import translate as deepl_web_Translator
from translators import translate_text as other_web_Translator
from .translation_languages import translatorEngine, translation_lang

# Translator
class Translator():
    def __init__(self):
        pass
        self.translator_status = {}

    def authentication(self, translator_name, authkey=None):
        result = True
        match translator_name:
            case "DeepL_API":
                try:
                    self.deepl_client = deepl_Translator(authkey)
                    self.deepl_client.translate_text(" ", target_lang="EN-US")
                except:
                    result = False
        return result

    def translate(self, translator_name, source_language, target_language, message):
        print(translator_name, source_language, target_language, message)
        try:
            result = ""
            source_language=translation_lang[translator_name]["source"][source_language]
            target_language=translation_lang[translator_name]["target"][target_language]
            match translator_name:
                case "DeepL":
                    result = deepl_web_Translator(
                        source_language=source_language,
                        target_language=target_language,
                        text=message
                        )
                case "DeepL_API":
                    result = self.deepl_client.translate_text(
                        message,
                        source_lang=source_language,
                        target_lang=target_language,
                        ).text
                case "Google":
                    result = other_web_Translator(
                        query_text=message,
                        translator="google",
                        from_language=source_language,
                        to_language=target_language,
                        )
                case "Bing":
                    result = other_web_Translator(
                        query_text=message,
                        translator="bing",
                        from_language=source_language,
                        to_language=target_language,
                        )
        except:
            result = False
        return result