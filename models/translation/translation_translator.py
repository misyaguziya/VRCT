import os
from deepl import Translator as deepl_Translator
from deepl_translate import translate as deepl_web_Translator
from translators import translate_text as other_web_Translator
from .translation_languages import translation_lang

import ctranslate2
import transformers

TRANSLATE_MODELS = {
    "small": "facebook/m2m100_418M",
    "large": "facebook/m2m100_1.2B"
}

# Translator
class Translator():
    def __init__(self, path, weight_config):
        self.translator_status = {}
        directory_name = weight_config["directory_name"]
        tokenizer = weight_config["tokenizer"]
        self.weight_path = os.path.join(path, "weight", directory_name)
        self.translator = ctranslate2.Translator(self.weight_path, device="cpu", device_index=0, compute_type="int8", inter_threads=1, intra_threads=4)
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(tokenizer)

    def authentication(self, translator_name, authkey=None):
        result = True
        match translator_name:
            case "DeepL_API":
                try:
                    self.deepl_client = deepl_Translator(authkey)
                    self.deepl_client.translate_text(" ", target_lang="EN-US")
                except Exception:
                    result = False
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
        except Exception:
            import traceback
            with open('error.log', 'a') as f:
                traceback.print_exc(file=f)
            result = False
        return result

    def translate_ctranslate2(self, translator_name, source_language, target_language, message):

        source_language=translation_lang["ctranslate2"]["source"][source_language]
        target_language=translation_lang["ctranslate2"]["target"][target_language]

        self.tokenizer.src_lang = source_language
        source = self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(message))
        target_prefix = [self.tokenizer.lang_code_to_token[target_language]]
        results = self.translator.translate_batch([source], target_prefix=[target_prefix])
        target = results[0].hypotheses[0][1:]

        result = self.tokenizer.decode(self.tokenizer.convert_tokens_to_ids(target))
        return result