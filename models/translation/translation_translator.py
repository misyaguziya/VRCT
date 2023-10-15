from deepl_translate import translate as deepl_web_Translator
from translators import translate_text as other_web_Translator
from .translation_languages import translatorEngine, translation_lang

# Translator
class Translator():
    def __init__(self):
        pass

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