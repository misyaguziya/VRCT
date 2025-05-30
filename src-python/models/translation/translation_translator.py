"""Provides a unified interface for various translation engines."""
from os import path as os_path
from typing import Any, Optional, Tuple, Union # Added Tuple, Union

import ctranslate2 # type: ignore
import transformers # For AutoTokenizer
import warnings

# Third-party libraries for translation
try:
    from deepl import DeepLClient # type: ignore
except ImportError:
    DeepLClient = None # type: ignore
    print("DeepL library not installed, DeepL API functionality will be unavailable.")

try:
    from translators import translate_text as other_web_Translator # type: ignore
    ENABLE_TRANSLATORS_LIB = True
except ImportError:
    ENABLE_TRANSLATORS_LIB = False
    def other_web_Translator(*args: Any, **kwargs: Any) -> str: # type: ignore
        errorLogging("Translators library not installed. Web-based translators (Google, Bing, etc.) are unavailable.")
        return "Error: Translators library not installed."
    print("Translators library not installed, web-based translation services (Google, Bing, etc.) will be unavailable.")


from .translation_languages import translation_lang as translation_lang_data # Aliased
from .translation_utils import ctranslate2_weights
from utils import errorLogging, getBestComputeType


warnings.filterwarnings("ignore", category=UserWarning, module='transformers.modeling_utils') # Filter specific warnings

class Translator:
    """
    A unified interface for accessing various translation services, including
    DeepL API, CTranslate2 models, and web-based translators via the 'translators' library.
    """
    deepl_client: Optional[Any] # Using Any if DeepLClient type causes issues, ideally deepl.DeepLClient
    ctranslate2_translator: Optional[ctranslate2.Translator]
    ctranslate2_tokenizer: Optional[transformers.PreTrainedTokenizerBase] # Or AutoTokenizer
    is_loaded_ctranslate2_model: bool
    is_enable_web_translators: bool # Renamed from is_enable_translators for clarity

    def __init__(self) -> None:
        """Initializes the Translator, setting up default states for translation engines."""
        self.deepl_client = None
        self.ctranslate2_translator = None
        self.ctranslate2_tokenizer = None
        self.is_loaded_ctranslate2_model = False
        self.is_enable_web_translators = ENABLE_TRANSLATORS_LIB

    def authenticationDeepLAuthKey(self, authkey: str) -> bool:
        """
        Authenticates with the DeepL API using the provided authentication key.

        Args:
            authkey: The DeepL API authentication key.

        Returns:
            True if authentication is successful, False otherwise.
        """
        if DeepLClient is None: # Check if library was imported
            errorLogging("DeepL library not available for authentication.")
            return False
        try:
            # Attempt to create a client and make a trivial request to validate the key
            client = DeepLClient(authkey)
            client.translate_text("test", target_lang="EN-US") # Target lang can be any supported
            self.deepl_client = client # Store client only on success
            return True
        except Exception as e:
            errorLogging(f"DeepL API authentication failed: {e}")
            self.deepl_client = None
            return False

    def changeCTranslate2Model(self, path: str, model_type: str, device: str = "cpu", device_index: int = 0) -> None:
        """
        Loads or changes the CTranslate2 model and tokenizer.

        Args:
            path: Root path where CTranslate2 model weights are stored.
            model_type: The type of CTranslate2 model to load (e.g., "small", "large").
            device: Compute device ("cpu" or "cuda").
            device_index: Index of the GPU if using CUDA.
        """
        self.is_loaded_ctranslate2_model = False
        weight_info = ctranslate2_weights.get(model_type)
        if not weight_info:
            errorLogging(f"Invalid CTranslate2 model type: {model_type}")
            return

        directory_name = str(weight_info["directory_name"])
        tokenizer_name = str(weight_info["tokenizer"])
        
        weight_path = os_path.join(path, "weights", "ctranslate2", directory_name)
        # Tokenizer is expected to be inside the model's weight directory after downloadCTranslate2Tokenizer
        tokenizer_cache_path = os_path.join(path, "weights", "ctranslate2", directory_name, "tokenizer")


        try:
            compute_type = getBestComputeType(device, device_index)
            self.ctranslate2_translator = ctranslate2.Translator(
                weight_path,
                device=device,
                device_index=device_index,
                compute_type=compute_type,
                inter_threads=1, # Default OpenMP threads used by CTranslate2
                intra_threads=4  # Default OpenMP threads used by CTranslate2
            )
            # Load tokenizer from the specific cache_dir where it was downloaded by downloadCTranslate2Tokenizer
            self.ctranslate2_tokenizer = transformers.AutoTokenizer.from_pretrained(tokenizer_name, cache_dir=tokenizer_cache_path, local_files_only=True)
            self.is_loaded_ctranslate2_model = True
            print(f"CTranslate2 model '{model_type}' and tokenizer '{tokenizer_name}' loaded successfully.")
        except Exception as e:
            errorLogging(f"Failed to load CTranslate2 model '{model_type}' or tokenizer '{tokenizer_name}': {e}")
            self.ctranslate2_translator = None
            self.ctranslate2_tokenizer = None
            self.is_loaded_ctranslate2_model = False


    def isLoadedCTranslate2Model(self) -> bool:
        """Checks if a CTranslate2 model is currently loaded."""
        return self.is_loaded_ctranslate2_model

    def translateCTranslate2(self, message: str, source_language: str, target_language: str) -> Union[str, bool]:
        """
        Translates a message using the loaded CTranslate2 model.

        Args:
            message: The text to translate.
            source_language: Source language code (e.g., "en", "ja").
            target_language: Target language code.

        Returns:
            The translated string, or False if translation fails.
        """
        if not self.is_loaded_ctranslate2_model or not self.ctranslate2_translator or not self.ctranslate2_tokenizer:
            errorLogging("CTranslate2 model or tokenizer not loaded for translation.")
            return False
        try:
            # Some models (like M2M100) require the source language to be set on the tokenizer
            if hasattr(self.ctranslate2_tokenizer, 'src_lang'):
                 self.ctranslate2_tokenizer.src_lang = source_language
            
            source_tokens = self.ctranslate2_tokenizer.convert_ids_to_tokens(self.ctranslate2_tokenizer.encode(message))
            
            # Target prefix for forced decoding (e.g., [[self.ctranslate2_tokenizer.lang_code_to_token[target_language]]])
            # This depends on the specific model and its tokenizer capabilities.
            # For M2M100, this is standard. For other models, it might differ or not be needed.
            target_prefix = [self.ctranslate2_tokenizer.lang_code_to_token[target_language]] # type: ignore
            
            results = self.ctranslate2_translator.translate_batch([source_tokens], target_prefix=[target_prefix])
            # Assuming the first hypothesis of the first batch item is the desired translation
            translated_tokens = results[0].hypotheses[0][1:] # Remove leading target language token
            
            translated_text = self.ctranslate2_tokenizer.decode(
                self.ctranslate2_tokenizer.convert_tokens_to_ids(translated_tokens)
            )
            return translated_text
        except Exception as e:
            errorLogging(f"CTranslate2 translation error: {e}")
            return False

    @classmethod
    def getLanguageCode(cls, translator_name: str, target_country: Optional[str], 
                        source_language: str, target_language: str) -> Tuple[str, str]:
        """
        Gets the specific language codes for a given translator, potentially adjusting for regional variations.

        Args:
            translator_name: Name of the translation engine (e.g., "DeepL_API", "Google").
            target_country: Target country code, used by some engines for regional language variants.
            source_language: Source language name (e.g., "English").
            target_language: Target language name (e.g., "Japanese").

        Returns:
            A tuple (source_lang_code, target_lang_code).
        """
        # Use .get for safer access with default empty dict if translator_name is not found
        source_lang_map = translation_lang_data.get(translator_name, {}).get("source", {})
        target_lang_map = translation_lang_data.get(translator_name, {}).get("target", {})

        # Default to original language name if code not found (should ideally not happen with well-defined maps)
        final_source_code = source_lang_map.get(source_language, source_language)
        final_target_code = target_lang_map.get(target_language, target_language)

        if translator_name == "DeepL_API":
            if target_language == "English":
                if target_country in ["United States", "Canada", "Philippines"]: # Common EN-US regions
                    final_target_code = target_lang_map.get("English American", "EN-US")
                else: # Default to British English for other regions
                    final_target_code = target_lang_map.get("English British", "EN-GB")
            elif target_language == "Portuguese":
                if target_country == "Portugal":
                    final_target_code = target_lang_map.get("Portuguese European", "PT-PT")
                else: # Default to Brazilian Portuguese for other regions (Brazil is largest)
                    final_target_code = target_lang_map.get("Portuguese Brazilian", "PT-BR")
        
        return str(final_source_code), str(final_target_code)


    def translate(self, translator_name: str, source_language: str, target_language: str, 
                  target_country: Optional[str], message: str) -> Union[str, bool]:
        """
        Translates a message using the specified engine, languages, and country.

        Args:
            translator_name: The name of the translation engine.
            source_language: The source language name (e.g., "English").
            target_language: The target language name (e.g., "Japanese").
            target_country: The target country (e.g., "US", "GB", "JP"), used for regional variations.
            message: The text message to translate.

        Returns:
            The translated string if successful, False otherwise.
        """
        try:
            # Get engine-specific language codes
            # These are now full language names, mapping to codes happens in getLanguageCode
            engine_source_lang, engine_target_lang = self.getLanguageCode(
                translator_name, target_country, source_language, target_language
            )

            translated_text: Union[str, bool] = False # Default to False for failure

            if not message.strip(): # Don't attempt to translate empty or whitespace-only messages
                return "" # Return empty string for empty input

            match translator_name:
                case "DeepL":
                    if self.is_enable_web_translators:
                        translated_text = other_web_Translator(
                            query_text=message,
                            translator="deepl",
                            from_language=engine_source_lang,
                            to_language=engine_target_lang,
                        )
                    else:
                        errorLogging("Web translators (including DeepL free) are not enabled.")
                        return False
                case "DeepL_API":
                    if self.deepl_client:
                        # Assuming deepl.DeepLClient.translate_text returns an object with a .text attribute
                        deepl_result = self.deepl_client.translate_text(
                            message,
                            source_lang=engine_source_lang, # API might expect uppercase, e.g., "EN"
                            target_lang=engine_target_lang, # e.g., "JA", "EN-US"
                        )
                        translated_text = deepl_result.text if deepl_result else False
                    else:
                        errorLogging("DeepL API client not authenticated or available.")
                        return False
                case "Google" | "Bing" | "Papago": # Group similar web translators
                    if self.is_enable_web_translators:
                        # Map our generic translator_name to the specific one for the library
                        lib_translator_name = translator_name.lower()
                        if lib_translator_name == "papago" and source_language == "English" and target_language == "Japanese":
                             # Papago has specific NMT (ko-ja, ja-ko) and SMT for others.
                             # The 'translators' library might handle this, or specific pairs might be better.
                             # For en-ja, it often uses a different engine or model.
                             # The library usually expects ISO codes for Papago.
                             pass # Let `other_web_Translator` handle it based on codes.

                        translated_text = other_web_Translator(
                            query_text=message,
                            translator=lib_translator_name,
                            from_language=engine_source_lang,
                            to_language=engine_target_lang,
                        )
                    else:
                        errorLogging(f"Web translators (including {translator_name}) are not enabled.")
                        return False
                case "CTranslate2":
                    translated_text = self.translateCTranslate2(
                        message=message,
                        source_language=engine_source_lang, # Expects codes like 'en', 'fra_Latn' etc.
                        target_language=engine_target_lang,
                    )
                case _:
                    errorLogging(f"Unknown translator_name: {translator_name}")
                    return False
            
            # Ensure result is string or False
            if isinstance(translated_text, str):
                return translated_text.strip() if translated_text else False # Return False if strip results in empty
            return False # If not string (e.g. None from some translator errors)

        except Exception as e:
            errorLogging(f"Error during translation with {translator_name}: {e}")
            return False