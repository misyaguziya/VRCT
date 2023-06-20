import deepl
import deepl_translate
import translators as ts

# Translator
class Translator():
    def __init__(self):
        self.translator_status = {
            "DeepL(web)": False,
            "DeepL(auth)": False,
            "Google(web)": False,
            "Bing(web)": False,
        }
        self.languages = {}
        self.languages["DeepL(web)"] = [
            "JA","EN","BG","ZH","CS","DA","NL","ET","FI","FR","DE","EL","HU","IT",
            "LV","LT","PL","PT","RO","RU","SK","SL","ES","SV",
        ]
        self.languages["DeepL(auth)"] = [
            "JA","EN-US","EN-GB","BG","CS","DA","DE","EL","ES","ET","FI","FR","HU",
            "ID","IT","KO","LT","LV","NB","NL","PL","PT","PT-BR","PT-PT","RO","RU",
            "SK","SL","SV","TR","UK","ZH",
        ]
        self.languages["Google(web)"] = [
            "ja","en","zh","ar","ru","fr","de","es","pt","it","ko","el","nl","hi",
            "tr","ms","th","vi","id","he","pl","mn","cs","hu","et","bg","da","fi",
            "ro","sv","sl","fa","bs","sr","tl","ht","ca","hr","lv","lt","ur","uk",
            "cy","sw","sm","sk","af","no","bn","mg","mt","gu","ta","te","pa","am",
            "az","be","ceb","eo","eu","ga"
        ]
        self.languages["Bing(web)"] = [
            "ja","en","zh","ar","ru","fr","de","es","pt","it","ko","el","nl","hi",
            "tr","ms","th","vi","id","he","pl","cs","hu","et","bg","da","fi","ro",
            "sv","sl","fa","bs","sr","fj","tl","ht","ca","hr","lv","lt","ur","uk",
            "cy","ty","to","sw","sm","sk","af","no","bn","mg","mt","otq","tlh","gu",
            "ta","te","pa","ga"
        ]
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
                result = deepl_translate.translate(source_language=source_language, target_language=target_language, text=message)
            elif translator_name == "DeepL(auth)":
                result = self.deepl_client.translate_text(message, source_lang=source_language, target_lang=target_language).text
            elif translator_name == "Google(web)":
                result = ts.translate_text(query_text=message, translator="google", from_language=source_language, to_language=target_language)
            elif translator_name == "Bing(web)":
                result = ts.translate_text(query_text=message, translator="bing", from_language=source_language, to_language=target_language)
        except:
            pass
        return result