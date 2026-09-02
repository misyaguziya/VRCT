from os import path as os_path
from deepl import DeepLClient

try:
    from .translation_languages import translation_lang
    from .translation_utils import ctranslate2_weights
    from .translation_bing import parse_bing_credentials
except Exception:
    import sys
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_languages import translation_lang
    from translation_utils import ctranslate2_weights
    from translation_bing import parse_bing_credentials

from utils import errorLogging, getBestComputeType

try:
    from translators import translate_text as other_web_Translator
    from translators.server import _bing as bing_translator
    bing_translator.get_tk = parse_bing_credentials
    ENABLE_TRANSLATORS = True
except Exception:
    other_web_Translator = None  # type: ignore
    bing_translator = None
    ENABLE_TRANSLATORS = False

import warnings
from threading import RLock
from typing import Any, Optional, Tuple

warnings.filterwarnings("ignore")


class UnsupportedLanguageError(Exception):
    """Raised when a language is not supported by the selected translator.

    Distinct from a translator backend failure (rate limit, network,
    authentication, provider error) so callers do not disable the
    translation engine just because the user picked a language it
    doesn't cover.
    """
    pass

try:
    import ctranslate2  # noqa: F401
except Exception:
    ctranslate2 = None  # type: ignore

try:
    import transformers  # noqa: F401
except Exception:
    transformers = None  # type: ignore

# 各プロバイダの LLM クライアント SDK は起動時にまとめて import する。
# try/except は Python パッケージ vs スクリプト実行の両方で動かすため
# (`from .module` と `from module` の両パターン)。PyInstaller の import
# scanner が静的に検出できるよう `from ... import Class` の形を維持する。
try:
    from .translation_plamo import PlamoClient
except Exception:
    from translation_plamo import PlamoClient

try:
    from .translation_gemini import GeminiClient
except Exception:
    from translation_gemini import GeminiClient

try:
    from .translation_openai import OpenAIClient
except Exception:
    from translation_openai import OpenAIClient

try:
    from .translation_openai_compatible import OpenAICompatibleClient
except Exception:
    from translation_openai_compatible import OpenAICompatibleClient

try:
    from .translation_groq import GroqClient
except Exception:
    from translation_groq import GroqClient

try:
    from .translation_openrouter import OpenRouterClient
except Exception:
    from translation_openrouter import OpenRouterClient

try:
    from .translation_lmstudio import LMStudioClient
except Exception:
    from translation_lmstudio import LMStudioClient

try:
    from .translation_ollama import OllamaClient
except Exception:
    from translation_ollama import OllamaClient


class Translator:
    """High-level translator facade.

    This class wraps multiple backends (DeepL API, Google, Bing, Papago,
    and CTranslate2 local models). Optional dependencies may be unavailable at
    runtime; methods degrade gracefully and return False or an empty string on
    failure (kept compatible with existing behavior).
    """

    def __init__(self) -> None:
        self.is_enable_translators = ENABLE_TRANSLATORS
        self.deepl_client: Optional[DeepLClient] = None
        self.plamo_client: Optional[Any] = None
        self.gemini_client: Optional[Any] = None
        self.openai_client: Optional[Any] = None
        self.openai_compatible_client: Optional[Any] = None
        self.groq_client: Optional[Any] = None
        self.openrouter_client: Optional[Any] = None
        self.lmstudio_client: Optional[Any] = None
        self.lmstudio_connected: bool = False
        self.ollama_client: Optional[Any] = None
        self.ollama_connected: bool = False
        self.ctranslate2_translator: Any = None
        self.ctranslate2_tokenizer: Any = None
        self.is_loaded_ctranslate2_model: bool = False
        self.is_changed_translator_parameters: bool = False
        # ctranslate2_translator/ctranslate2_tokenizer は mic/speaker の
        # _print_transcript スレッドと mainloop ワーカー (チャット送信) から
        # 同時に触られる共有状態。tokenizer.src_lang への代入は tokenizer
        # インスタンス自体の状態を書き換えるため、無ロックだと mic/speaker
        # 間で src_lang が競合して意図しない言語で encode/decode されたり
        # (クラッシュせず気付きにくい翻訳品質の劣化)、changeCTranslate2Model()
        # によるモデル差し替え中の破棄途中オブジェクトに translate_batch が
        # 入りうる。CTranslate2 の Translator 自体はスレッドセーフだが、
        # これは tokenizer の保護にはならない。RLock なのは、将来
        # 呼び出し元が既にロックを保持した状態で再入する可能性に備えるため
        # (現状のコードパスでは再入は起きない)。
        self._ctranslate2_lock: RLock = RLock()

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

    def authenticationPlamoAuthKey(self, auth_key: str, root_path: str = None) -> bool:
        """Authenticate Plamo API with the provided key.

        Returns True on success, False on failure.
        """
        self.plamo_client = PlamoClient(root_path=root_path)
        if self.plamo_client.setAuthKey(auth_key):
            return True
        else:
            self.plamo_client = None
            return False

    def getPlamoModelList(self) -> list[str]:
        """Get available Plamo models.

        Returns a list of model names, or an empty list on failure.
        """
        if self.plamo_client is None:
            return []
        return self.plamo_client.getModelList()

    def setPlamoModel(self, model: str) -> bool:
        """Change the Plamo model used for translation.

        Returns True on success, False on failure.
        """
        if self.plamo_client is None:
            return False
        return self.plamo_client.setModel(model)

    def updatePlamoClient(self) -> None:
        """Update the Plamo client (fetch available models)."""
        self.plamo_client.updateClient()

    def authenticationGeminiAuthKey(self, auth_key: str, root_path: str = None) -> bool:
        """Authenticate Gemini API with the provided key.

        Returns True on success, False on failure.
        """
        self.gemini_client = GeminiClient(root_path=root_path)
        if self.gemini_client.setAuthKey(auth_key):
            return True
        else:
            self.gemini_client = None
            return False

    def getGeminiModelList(self) -> list[str]:
        """Get available Gemini models.

        Returns a list of model names, or an empty list on failure.
        """
        if self.gemini_client is None:
            return []
        return self.gemini_client.getModelList()

    def setGeminiModel(self, model: str) -> bool:
        """Change the Gemini model used for translation.

        Returns True on success, False on failure.
        """
        if self.gemini_client is None:
            return False
        return self.gemini_client.setModel(model)

    def updateGeminiClient(self) -> None:
        """Update the Gemini client (fetch available models)."""
        self.gemini_client.updateClient()

    def authenticationOpenAIAuthKey(self, auth_key: str, base_url: str | None = None, root_path: str = None) -> bool:
        """Authenticate OpenAI (Chat Completions) API with the provided key.

        base_url を指定することで互換エンドポイント (例: Azure OpenAI 互換, Proxy) にも対応可能。
        Returns True on success, False on failure.
        """
        self.openai_client = OpenAIClient(base_url=base_url, root_path=root_path)
        if self.openai_client.setAuthKey(auth_key):
            return True
        else:
            self.openai_client = None
            return False

    def getOpenAIModelList(self) -> list[str]:
        """Get available OpenAI models.

        Returns a list of model names, or an empty list on failure.
        """
        if self.openai_client is None:
            return []
        return self.openai_client.getModelList()

    def setOpenAIModel(self, model: str) -> bool:
        """Change the OpenAI model used for translation.

        Returns True on success, False on failure.
        """
        if self.openai_client is None:
            return False
        return self.openai_client.setModel(model)

    def updateOpenAIClient(self) -> None:
        """Update the OpenAI client (fetch available models)."""
        self.openai_client.updateClient()

    def authenticationOpenAICompatibleAuthKey(self, auth_key: str, base_url: str | None = None, root_path: str = None) -> bool:
        """Authenticate an OpenAI-compatible endpoint with the provided key and base URL.

        `base_url` は必須想定（None の場合は公式エンドポイントにフォールバック）。
        Returns True on success, False on failure.
        """
        self.openai_compatible_client = OpenAICompatibleClient(base_url=base_url, root_path=root_path)
        if self.openai_compatible_client.setAuthKey(auth_key):
            return True
        else:
            self.openai_compatible_client = None
            return False

    def getOpenAICompatibleModelList(self) -> list[str]:
        """Get available OpenAI-compatible endpoint models."""
        if self.openai_compatible_client is None:
            return []
        return self.openai_compatible_client.getModelList()

    def setOpenAICompatibleModel(self, model: str) -> bool:
        """Change the OpenAI-compatible model used for translation."""
        if self.openai_compatible_client is None:
            return False
        return self.openai_compatible_client.setModel(model)

    def updateOpenAICompatibleClient(self) -> None:
        """Update the OpenAI-compatible client (fetch available models)."""
        self.openai_compatible_client.updateClient()

    def authenticationGroqAuthKey(self, auth_key: str, root_path: str = None) -> bool:
        """Authenticate Groq API with the provided key.

        Returns True on success, False on failure.
        """
        self.groq_client = GroqClient(root_path=root_path)
        if self.groq_client.setAuthKey(auth_key):
            return True
        else:
            self.groq_client = None
            return False

    def getGroqModelList(self) -> list[str]:
        """Get available Groq models.

        Returns a list of model names, or an empty list on failure.
        """
        if self.groq_client is None:
            return []
        return self.groq_client.getModelList()

    def setGroqModel(self, model: str) -> bool:
        """Change the Groq model used for translation.

        Returns True on success, False on failure.
        """
        if self.groq_client is None:
            return False
        return self.groq_client.setModel(model)

    def updateGroqClient(self) -> None:
        """Update the Groq client (fetch available models)."""
        self.groq_client.updateClient()

    def authenticationOpenRouterAuthKey(self, auth_key: str, root_path: str = None) -> bool:
        """Authenticate OpenRouter API with the provided key.

        Returns True on success, False on failure.
        """
        self.openrouter_client = OpenRouterClient(root_path=root_path)
        if self.openrouter_client.setAuthKey(auth_key):
            return True
        else:
            self.openrouter_client = None
            return False

    def getOpenRouterModelList(self) -> list[str]:
        """Get available OpenRouter models.

        Returns a list of model names, or an empty list on failure.
        """
        if self.openrouter_client is None:
            return []
        return self.openrouter_client.getModelList()

    def setOpenRouterModel(self, model: str) -> bool:
        """Change the OpenRouter model used for translation.

        Returns True on success, False on failure.
        """
        if self.openrouter_client is None:
            return False
        return self.openrouter_client.setModel(model)

    def updateOpenRouterClient(self) -> None:
        """Update the OpenRouter client (fetch available models)."""
        self.openrouter_client.updateClient()

    def getLMStudioConnected(self) -> bool:
        """Get LM Studio connection status.

        Returns True if connected and verified, False otherwise.
        """
        return self.lmstudio_connected

    def setLMStudioClientURL(self, base_url: str | None = None, root_path: str = None) -> bool:
        """Authenticate LM Studio with the provided base URL.

        Returns True on success, False on failure.
        """
        self.lmstudio_client = LMStudioClient(base_url=base_url, root_path=root_path)
        result = self.lmstudio_client.setBaseURL(base_url)
        if result is False:
            self.lmstudio_client = None
            self.lmstudio_connected = False
        else:
            self.lmstudio_connected = True
        return result

    def getLMStudioModelList(self) -> list[str]:
        """Get available LM Studio models.

        Returns a list of model names, or an empty list on failure.
        """
        if self.lmstudio_client is None:
            return []
        return self.lmstudio_client.getModelList()

    def setLMStudioModel(self, model: str) -> bool:
        """Change the LM Studio model used for translation.
        """
        if self.lmstudio_client is None:
            return False
        return self.lmstudio_client.setModel(model)

    def updateLMStudioClient(self) -> None:
        """Update the LM Studio client (fetch available models)."""
        self.lmstudio_client.updateClient()

    def getOllamaConnected(self) -> bool:
        """Get Ollama connection status.

        Returns True if connected and verified, False otherwise.
        """
        return self.ollama_connected

    def checkOllamaClient(self, root_path: str = None) -> bool:
        """Check if Ollama client is available.

        Returns True if Ollama is reachable, False otherwise.
        """
        self.ollama_client = OllamaClient(root_path=root_path)
        result = self.ollama_client.authenticationCheck()
        if result is False:
            self.ollama_client = None
            self.ollama_connected = False
        else:
            self.ollama_connected = True
        return result

    def getOllamaModelList(self, root_path: str = None) -> bool:
        """Initialize Ollama client and fetch available models.

        Returns True on success, False on failure.
        """
        if self.ollama_client is None:
            return []
        return self.ollama_client.getModelList()

    def setOllamaModel(self, model: str) -> bool:
        """Change the Ollama model used for translation.

        Returns True on success, False on failure.
        """
        if self.ollama_client is None:
            return False
        return self.ollama_client.setModel(model)

    def updateOllamaClient(self) -> None:
        """Update the Ollama client (fetch available models)."""
        self.ollama_client.updateClient()

    def changeCTranslate2Model(self, path: str, model_type: str, device: str = "cpu", device_index: int = 0, compute_type: str = "auto") -> None:
        """Load a CTranslate2 model from weights.

        This sets internal translator/tokenizer objects and flips
        ``is_loaded_ctranslate2_model`` on success.
        """
        if ctranslate2 is None or transformers is None:
            return

        with self._ctranslate2_lock:
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
        with self._ctranslate2_lock:
            if self.is_loaded_ctranslate2_model is True:
                try:
                    self.ctranslate2_tokenizer.src_lang = source_language
                    source = self.ctranslate2_tokenizer.convert_ids_to_tokens(self.ctranslate2_tokenizer.encode(message))
                    match weight_type:
                        case "m2m100_418M-ct2-int8" | "m2m100_1.2B-ct2-int8":
                            target_prefix = [self.ctranslate2_tokenizer.lang_code_to_token[target_language]]
                        case "nllb-200-distilled-600M-ct2-int8" | "nllb-200-distilled-1.3B-ct2-int8" | "nllb-200-3.3B-ct2-int8":
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

        Raises:
            UnsupportedLanguageError: `source_language`/`target_language` is
                not in this translator's supported language table.
        """
        try:
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
                    source_language = translation_lang[translator_name]["source"][source_language]
                    target_language = translation_lang[translator_name]["target"][target_language]
                case "CTranslate2":
                    source_language = translation_lang[translator_name][weight_type]["source"][source_language]
                    target_language = translation_lang[translator_name][weight_type]["target"][target_language]
                case _:
                    source_language = translation_lang[translator_name]["source"][source_language]
                    target_language = translation_lang[translator_name]["target"][target_language]
        except KeyError as e:
            raise UnsupportedLanguageError(
                f"{translator_name} does not support language {e} (source={source_language!r}, target={target_language!r})"
            ) from e
        return source_language, target_language

    def translate(self, translator_name: str, weight_type: str, source_language: str, target_language: str, target_country: str, message: str, context_history: Optional[list[dict]] = None) -> Any:
        """Translate `message` using the named translator backend.

        Args:
            translator_name: Name of the translator backend to use
            weight_type: Model weight type for CTranslate2
            source_language: Source language name
            target_language: Target language name
            target_country: Target country for locale-specific translations
            message: Text to translate
            context_history: Optional conversation context (Chat/Mic/Speaker messages)

        Returns translated string on success. Returns None if the language
        pair is not supported by this translator (not a backend failure).
        Returns False on an actual backend failure (rate limit, network,
        authentication, provider error). When source_language ==
        target_language the original message is returned.
        """
        try:
            if source_language == target_language:
                return message

            result: Any = ""
            source_language, target_language = self.getLanguageCode(translator_name, weight_type, target_country, source_language, target_language)
            match translator_name:
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
                        if context_history:
                            self.plamo_client.setContextHistory(context_history)
                        result = self.plamo_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                            )
                case "Gemini_API":
                    if self.gemini_client is None:
                        result = False
                    else:
                        if context_history:
                            self.gemini_client.setContextHistory(context_history)
                        result = self.gemini_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                            )
                case "OpenAI_API":
                    if self.openai_client is None:
                        result = False
                    else:
                        if context_history:
                            self.openai_client.setContextHistory(context_history)
                        result = self.openai_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "OpenAI_Compatible":
                    if self.openai_compatible_client is None:
                        result = False
                    else:
                        if context_history:
                            self.openai_compatible_client.setContextHistory(context_history)
                        result = self.openai_compatible_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "Groq_API":
                    if self.groq_client is None:
                        result = False
                    else:
                        if context_history:
                            self.groq_client.setContextHistory(context_history)
                        result = self.groq_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "OpenRouter_API":
                    if self.openrouter_client is None:
                        result = False
                    else:
                        if context_history:
                            self.openrouter_client.setContextHistory(context_history)
                        result = self.openrouter_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "LMStudio":
                    if self.lmstudio_client is None:
                        result = False
                    else:
                        if context_history:
                            self.lmstudio_client.setContextHistory(context_history)
                        result = self.lmstudio_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "Ollama":
                    if self.ollama_client is None:
                        result = False
                    else:
                        if context_history:
                            self.ollama_client.setContextHistory(context_history)
                        result = self.ollama_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "Google":
                    if ENABLE_TRANSLATORS is True and other_web_Translator is not None:
                        result = other_web_Translator(
                            query_text=message,
                            translator="google",
                            from_language=source_language,
                            to_language=target_language,
                        )
                case "Bing":
                    if ENABLE_TRANSLATORS is True and other_web_Translator is not None:
                        result = other_web_Translator(
                            query_text=message,
                            translator="bing",
                            from_language=source_language,
                            to_language=target_language,
                        )
                case "Papago":
                    if ENABLE_TRANSLATORS is True and other_web_Translator is not None:
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
        except UnsupportedLanguageError:
            result = None
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