import deepl
import deepl_translate
import translators as ts
import languages

# Translator
class Translator():
    def __init__(self):
        self.translator_status = {
            "DeepL(web)": False,
            "DeepL(auth)": False,
            "Google(web)": False,
            "Bing(web)": False,
        }

        self.dict_languages = {}
        self.dict_languages["DeepL(web)"] = languages.deepl_translate_lang
        self.dict_languages["DeepL(auth)"] = languages.deepl_lang
        self.dict_languages["Google(web)"] = languages.translators_google_lang
        self.dict_languages["Bing(web)"] = languages.translators_bing_lang

        self.languages = {}
        self.languages["DeepL(web)"] = list(self.dict_languages["DeepL(web)"].keys())
        self.languages["DeepL(auth)"] = list(self.dict_languages["DeepL(auth)"].keys())
        self.languages["Google(web)"] = list(self.dict_languages["Google(web)"].keys())
        self.languages["Bing(web)"] = list(self.dict_languages["Bing(web)"].keys())
        self.deepl_client = None

    def authentication(self, translator_name, authkey=None):
        result = False
        try:
            if translator_name == "DeepL(web)":
                self.translator_status["DeepL(web)"] = True
                result = True
            elif translator_name == "DeepL(auth)":
                self.deepl_client = deepl.Translator(authkey)
                self.deepl_client.translate_text(" ", target_lang="EN-US")
                self.translator_status["DeepL(auth)"] = True
                result = True
            elif translator_name == "Google(web)":
                self.translator_status["Google(web)"] = True
                result = True
            elif translator_name == "Bing(web)":
                self.translator_status["Bing(web)"] = True
                result = True
        except:
            pass
        return result

    def translate(self, translator_name, source_language, target_language, message):
        result = False
        try:
            if translator_name == "DeepL(web)":
                result = deepl_translate.translate(
                    source_language=self.dict_languages["DeepL(web)"][source_language],
                    target_language=self.dict_languages["DeepL(web)"][target_language],
                    text=message
                    )
            elif translator_name == "DeepL(auth)":
                result = self.deepl_client.translate_text(
                    message,
                    source_lang=self.dict_languages["DeepL(auth)"][source_language],
                    target_lang=self.dict_languages["DeepL(auth)"][target_language],
                    ).text
            elif translator_name == "Google(web)":
                result = ts.translate_text(
                    query_text=message,
                    translator="google",
                    from_language=self.dict_languages["Google(web)"][source_language],
                    to_language=self.dict_languages["Google(web)"][target_language],
                    )
            elif translator_name == "Bing(web)":
                result = ts.translate_text(
                    query_text=message,
                    translator="bing",
                    from_language=self.dict_languages["Bing(web)"][source_language],
                    to_language=self.dict_languages["Bing(web)"][target_language],
                    )
        except:
            pass
        return result