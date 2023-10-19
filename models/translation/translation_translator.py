from deepl import Translator as deepl_Translator
from deepl_translate import translate as deepl_web_Translator
from translators import translate_text as other_web_Translator
from .translation_languages import translatorEngine, translation_lang

# Translator
class Translator():
    def __init__(self):
        self.translator_status = {}
        for translator in translatorEngine:
            self.translator_status[translator] = False
        self.deepl_client = None

    def authentication(self, translator_name, authkey=None):
        result = False
        match translator_name:
            case "DeepL":
                self.translator_status[translator_name] = True
                result = True
            case "DeepL_API":
                try:
                    self.deepl_client = deepl_Translator(authkey)
                    self.deepl_client.translate_text(" ", target_lang="EN-US")
                    self.translator_status[translator_name] = True
                    result = True
                except:
                    self.translator_status[translator_name] = False
            case "Google":
                self.translator_status[translator_name] = True
                result = True
            case "Bing":
                self.translator_status[translator_name] = True
                result = True
        return result

    def translate(self, translator_name, source_language, target_language, message):
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
            pass
        return result