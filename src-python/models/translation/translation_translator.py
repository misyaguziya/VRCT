from os import path as os_path
from deepl import DeepLClient
try:
    from translators import translate_text as other_web_Translator
    ENABLE_TRANSLATORS = True
except Exception:
    other_web_Translator = None  # type: ignore
    ENABLE_TRANSLATORS = False

try:
    from .translation_languages import translation_lang
    from .translation_utils import ctranslate2_weights
    from .translation_plamo import PlamoClient
    from .translation_gemini import GeminiClient
except Exception:
    import sys
    print(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_languages import translation_lang
    from translation_utils import ctranslate2_weights
    from translation_plamo import PlamoClient
    from translation_gemini import GeminiClient

import ctranslate2
import transformers
from utils import errorLogging, getBestComputeType

import warnings
from typing import Any, Optional, Tuple

warnings.filterwarnings("ignore")


class Translator:
    """High-level translator facade.

    This class wraps multiple backends (DeepL, DeepL API, Google, Bing, Papago,
    and CTranslate2 local models). Optional dependencies may be unavailable at
    runtime; methods degrade gracefully and return False or an empty string on
    failure (kept compatible with existing behavior).
    """

    def __init__(self) -> None:
        self.deepl_client: Optional[DeepLClient] = None
        self.plamo_client: Optional[PlamoClient] = None
        self.gemini_client: Optional[GeminiClient] = None
        self.ctranslate2_translator: Any = None
        self.ctranslate2_tokenizer: Any = None
        self.is_loaded_ctranslate2_model: bool = False
        self.is_changed_translator_parameters: bool = False
        self.is_enable_translators: bool = ENABLE_TRANSLATORS

    def authenticationDeepLAuthKey(self, auth_key: str) -> bool:
        """Authenticate DeepL API with the provided key.

        Returns True on success, False on failure.
        """
        result = True
        try:
            self.deepl_client = DeepLClient(auth_key)
            # quick smoke test
            self.deepl_client.translate_text(" ", target_lang="EN-US")
        except Exception:
            errorLogging()
            self.deepl_client = None
            result = False
        return result

    def authenticationPlamoAuthKey(self, auth_key: str, model: str) -> bool:
        """Authenticate Plamo API with the provided key.

        Returns True on success, False on failure.
        """
        result = True
        try:
            self.plamo_client = PlamoClient(auth_key, model=model)
            self.plamo_client.checkAuthKey()
        except Exception:
            errorLogging()
            self.plamo_client = None
            result = False
        return result

    def authenticationGeminiAuthKey(self, auth_key: str, model: str) -> bool:
        """Authenticate Gemini API with the provided key.

        Returns True on success, False on failure.
        """
        result = True
        try:
            self.gemini_client = GeminiClient(auth_key, model=model)
            self.gemini_client.checkAuthKey()
        except Exception:
            errorLogging()
            self.gemini_client = None
            result = False
        return result

    def changeCTranslate2Model(self, path: str, model_type: str, device: str = "cpu", device_index: int = 0, compute_type: str = "auto") -> None:
        """Load a CTranslate2 model from weights.

        This sets internal translator/tokenizer objects and flips
        ``is_loaded_ctranslate2_model`` on success.
        """
        self.is_loaded_ctranslate2_model = False
        directory_name = ctranslate2_weights[model_type]["directory_name"]
        tokenizer = ctranslate2_weights[model_type]["tokenizer"]
        weight_path = os_path.join(path, "weights", "ctranslate2", directory_name)
        tokenizer_path = os_path.join(path, "weights", "ctranslate2", directory_name, "tokenizer")

        if compute_type == "auto":
            compute_type = getBestComputeType(device, device_index)
        self.ctranslate2_translator = ctranslate2.Translator(
            weight_path,
            device=device,
            device_index=device_index,
            compute_type=compute_type,
            inter_threads=1,
            intra_threads=4,
        )
        try:
            self.ctranslate2_tokenizer = transformers.AutoTokenizer.from_pretrained(tokenizer, cache_dir=tokenizer_path)
        except Exception:
            errorLogging()
            tokenizer_path = os_path.join("./weights", "ctranslate2", directory_name, "tokenizer")
            self.ctranslate2_tokenizer = transformers.AutoTokenizer.from_pretrained(tokenizer, cache_dir=tokenizer_path)
        self.is_loaded_ctranslate2_model = True

    def isLoadedCTranslate2Model(self) -> bool:
        return self.is_loaded_ctranslate2_model

    def isChangedTranslatorParameters(self) -> bool:
        return self.is_changed_translator_parameters

    def setChangedTranslatorParameters(self, is_changed: bool) -> None:
        self.is_changed_translator_parameters = is_changed

    def translateCTranslate2(self, message: str, source_language: str, target_language, weight_type: str) -> Any:
        """Translate using a loaded CTranslate2 model.

        Returns a string on success or False on failure (keeps legacy behavior).
        """
        result: Any = False
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
    def getLanguageCode(translator_name: str, weight_type: str, target_country: str, source_language: str, target_language: str) -> Tuple[str, str]:
        """Resolve a friendly language name to translator-specific codes.

        Returns (source_code, target_code).
        """
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
        source_language = translation_lang[translator_name]["source"][source_language]
        target_language = translation_lang[translator_name]["target"][target_language]
        return source_language, target_language

    def translate(self, translator_name: str, weight_type: str, source_language: str, target_language: str, target_country: str, message: str) -> Any:
        """Translate `message` using the named translator backend.

        Returns translated string on success, or False on failure. When
        source_language == target_language the original message is returned.
        """
        try:
            if source_language == target_language:
                return message

            result: Any = ""
            source_language, target_language = self.getLanguageCode(translator_name, weight_type, target_country, source_language, target_language)
            match translator_name:
                case "DeepL":
                    if self.is_enable_translators is True and other_web_Translator is not None:
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
                                target_lang=target_language
                                ).text
                case "Plamo_API":
                    if self.plamo_client is None:
                        result = False
                    else:
                        result = self.plamo_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                            )
                case "Gemini_API":
                    if self.gemini_client is None:
                        result = False
                    else:
                        result = self.gemini_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                            )
                case "Google":
                    if self.is_enable_translators is True and other_web_Translator is not None:
                        result = other_web_Translator(
                            query_text=message,
                            translator="google",
                            from_language=source_language,
                            to_language=target_language,
                        )
                case "Bing":
                    if self.is_enable_translators is True and other_web_Translator is not None:
                        result = other_web_Translator(
                            query_text=message,
                            translator="bing",
                            from_language=source_language,
                            to_language=target_language,
                        )
                case "Papago":
                    if self.is_enable_translators is True and other_web_Translator is not None:
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