from os import path as os_path
from deepl import DeepLClient
try:
    from translators import translate_text as other_web_Translator
    ENABLE_TRANSLATORS = True
except Exception:
    ENABLE_TRANSLATORS = False

try:
    from .translation_languages import translation_lang
    from .translation_utils import ctranslate2_weights
    from .translation_plamo import PlamoClient
except Exception:
    import sys
    print(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_languages import translation_lang
    from translation_utils import ctranslate2_weights
    from translation_plamo import PlamoClient

import ctranslate2
import transformers
from utils import errorLogging, getBestComputeType

import warnings
warnings.filterwarnings("ignore")

# Translator
class Translator():
    def __init__(self):
        self.deepl_client = None
        self.plamo_client = None
        self.ctranslate2_translator = None
        self.ctranslate2_tokenizer = None
        self.is_loaded_ctranslate2_model = False
        self.is_enable_translators = ENABLE_TRANSLATORS

    def authenticationDeepLAuthKey(self, authkey):
        result = True
        try:
            self.deepl_client = DeepLClient(authkey)
            self.deepl_client.translate_text("Hello World", target_lang="EN-US")
        except Exception:
            errorLogging()
            self.deepl_client = None
            result = False
        return result

    def authenticationPlamoAuthKey(self, authkey):
        result = True
        try:
            self.plamo_client = PlamoClient(authkey)
            self.plamo_client.translate_text("Hello World", target_lang="English")
        except Exception:
            errorLogging()
            self.plamo_client = None
            result = False
        return result

    def changeCTranslate2Model(self, path, model_type, device="cpu", device_index=0):
        self.is_loaded_ctranslate2_model = False
        directory_name = ctranslate2_weights[model_type]["directory_name"]
        tokenizer = ctranslate2_weights[model_type]["tokenizer"]
        weight_path = os_path.join(path, "weights", "ctranslate2", directory_name)
        tokenizer_path = os_path.join(path, "weights", "ctranslate2", directory_name, "tokenizer")

        compute_type = getBestComputeType(device, device_index)
        self.ctranslate2_translator = ctranslate2.Translator(
            weight_path,
            device=device,
            device_index=device_index,
            compute_type=compute_type,
            inter_threads=1,
            intra_threads=4
        )
        try:
            self.ctranslate2_tokenizer = transformers.AutoTokenizer.from_pretrained(tokenizer, cache_dir=tokenizer_path)
        except Exception:
            errorLogging()
            tokenizer_path = os_path.join("./weights", "ctranslate2", directory_name, "tokenizer")
            self.ctranslate2_tokenizer = transformers.AutoTokenizer.from_pretrained(tokenizer, cache_dir=tokenizer_path)
        self.is_loaded_ctranslate2_model = True

    def isLoadedCTranslate2Model(self):
        return self.is_loaded_ctranslate2_model

    def translateCTranslate2(self, message, source_language, target_language, weight_type):
        result = False
        if self.is_loaded_ctranslate2_model is True:
            try:
                self.ctranslate2_tokenizer.src_lang = source_language
                source = self.ctranslate2_tokenizer.convert_ids_to_tokens(self.ctranslate2_tokenizer.encode(message))
                match weight_type:
                    case "m2m100_418M-ct2-int8" | "m2m100_1.2B-ct2-int8":
                        target_prefix = [self.ctranslate2_tokenizer.lang_code_to_token[target_language]]
                    case "nllb-200-distilled-1.3B-ct2-int8" | "nllb-200-3.3B-ct2-int8":
                        target_prefix = [target_language]
                    case _:
                        return False
                results = self.ctranslate2_translator.translate_batch([source], target_prefix=[target_prefix])
                target = results[0].hypotheses[0][1:]
                result = self.ctranslate2_tokenizer.decode(self.ctranslate2_tokenizer.convert_tokens_to_ids(target))
            except Exception:
                errorLogging()
        return result

    @staticmethod
    def getLanguageCode(translator_name, weight_type, target_country, source_language, target_language):
        match translator_name:
            case "DeepL_API":
                if target_language == "English":
                    if target_country in ["United States", "Canada", "Philippines"]:
                        target_language = "English American"
                    else:
                        target_language = "English British"
                elif target_language == "Portuguese":
                    if target_country in ["Portugal"]:
                        target_language = "Portuguese European"
                    else:
                        target_language = "Portuguese Brazilian"
            case "CTranslate2":
                translator_name = weight_type
            case _:
                pass
        source_language=translation_lang[translator_name]["source"][source_language]
        target_language=translation_lang[translator_name]["target"][target_language]
        return source_language, target_language

    def translate(self, translator_name, weight_type, source_language, target_language, target_country, message):
        try:
            result = ""
            source_language, target_language = self.getLanguageCode(translator_name, weight_type, target_country, source_language, target_language)
            match translator_name:
                case "DeepL":
                    if self.is_enable_translators is True:
                        result = other_web_Translator(
                            query_text=message,
                            translator="deepl",
                            from_language=source_language,
                            to_language=target_language,
                            )
                case "DeepL_API":
                    if self.is_enable_translators is True:
                        if self.deepl_client is None:
                            result = False
                        else:
                            result = self.deepl_client.translate_text(
                                message,
                                source_lang=source_language,
                                target_lang=target_language,
                                ).text
                case "Plamo_API":
                    if self.plamo_client is None:
                        result = False
                    else:
                        result = self.plamo_client.translate_text(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                            )
                case "Google":
                    if self.is_enable_translators is True:
                        result = other_web_Translator(
                            query_text=message,
                            translator="google",
                            from_language=source_language,
                            to_language=target_language,
                            )
                case "Bing":
                    if self.is_enable_translators is True:
                        result = other_web_Translator(
                            query_text=message,
                            translator="bing",
                            from_language=source_language,
                            to_language=target_language,
                            )
                case "Papago":
                    if self.is_enable_translators is True:
                        result = other_web_Translator(
                            query_text=message,
                            translator="papago",
                            from_language=source_language,
                            to_language=target_language,
                            )
                case "CTranslate2":
                    result = self.translateCTranslate2(
                        message=message,
                        source_language=source_language,
                        target_language=target_language,
                        weight_type=weight_type,
                        )
        except Exception:
            errorLogging()
            result = False
        return result

if __name__ == "__main__":
    translator = Translator()
    # test CTranslate2 model nllb-200-distilled-1.3B-ct2-int8
    translator.changeCTranslate2Model(path=".", model_type="nllb-200-distilled-1.3B-ct2-int8", device="cpu", device_index=0)
    result = translator.translate(
        translator_name="CTranslate2",
        weight_type="nllb-200-distilled-1.3B-ct2-int8",
        source_language="English",
        target_language="Japanese",
        target_country="Japan",
        message="Hello, world!"
        )
    print(result)