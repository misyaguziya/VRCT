import logging
from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from .translation_languages import translation_lang
    from .translation_utils import loadTranslatePromptConfig
except Exception:
    import sys
    from os import path as os_path
    print(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_languages import translation_lang
    from translation_utils import loadTranslatePromptConfig

logger = logging.getLogger("langchain_google_genai")
logger.setLevel(logging.ERROR)

def _authentication_check(api_key: str) -> bool:
    """Check if the provided API key is valid by attempting to list models.
    """
    try:
        client = genai.Client(api_key=api_key)
        client.models.list()
        return True
    except Exception:
        return False

def _get_available_text_models(api_key: str) -> list[str]:
    """Extract only Gemini models suitable for translation and chat applications
    """
    client = genai.Client(api_key=api_key)
    res = client.models.list()
    allowed_models = []

    # 除外対象のキーワード
    exclude_keywords = [
        "audio",
        "image",
        "veo",
        "tts",
        "robotics",
        "computer-use"
    ]
    for model in res:
        model_id = model.name
        if ("gemini" in model_id.lower() or "gemma" in model_id.lower()) and "generateContent" in model.supported_actions:
            if any(x in model_id for x in exclude_keywords):
                continue
            allowed_models.append(model_id.replace("models/", ""))
    allowed_models.sort()
    return allowed_models

class GeminiClient:
    def __init__(self, root_path: str = None):
        self.api_key = None
        self.model = None

        # プロンプト設定をYAMLファイルから読み込む
        prompt_config = loadTranslatePromptConfig(root_path, "translation_gemini.yml")
        self.supported_languages = list(translation_lang["Gemini_API"]["source"].keys())
        self.prompt_template = prompt_config["system_prompt"]
        # history config (optional)
        self.history_cfg = prompt_config.get("history", {
            "use_history": False,
            "sources": [],
            "max_messages": 0,
            "max_chars": 0,
            "header_template": "",
            "item_template": "[{source}] {role}: {text}",
        })
        self._context_history: list[dict] = []

        self.gemini_llm = None

    def getModelList(self) -> list[str]:
        return _get_available_text_models(self.api_key)

    def getAuthKey(self) -> str:
        return self.api_key

    def setAuthKey(self, api_key: str) -> bool:
        result = _authentication_check(api_key)
        if result:
            self.api_key = api_key
        return result

    def getModel(self) -> str:
        return self.model

    def setModel(self, model: str) -> bool:
        if model in self.getModelList():
            self.model = model
            return True
        else:
            return False

    def updateClient(self) -> None:
        self.gemini_llm = ChatGoogleGenerativeAI(
            model=self.model,
            api_key=self.api_key,
        )

    def setContextHistory(self, history_items: list[dict]) -> None:
        """Set recent conversation history for prompt injection.

        Each item should be a dict containing:
        - source: "chat" | "mic" | "speaker"
        - text: message string
        - timestamp: ISO format datetime string
        """
        self._context_history = history_items or []

    def translate(self, text: str, input_lang: str, output_lang: str) -> str:
        system_prompt = self.prompt_template.format(
            supported_languages=self.supported_languages,
            input_lang=input_lang,
            output_lang=output_lang
        )

        # Inject recent conversation history if enabled by YAML config
        if self.history_cfg.get("use_history"):
            allowed_sources = set(self.history_cfg.get("sources", []))
            max_messages = int(self.history_cfg.get("max_messages", 0))
            max_chars = int(self.history_cfg.get("max_chars", 0))
            item_tmpl = self.history_cfg.get("item_template", "[{source}] {role}: {text}")
            header_tmpl = self.history_cfg.get("header_template", "{history}")

            filtered = [h for h in self._context_history if h.get("source") in allowed_sources]
            recent = filtered[-max_messages:] if max_messages > 0 else filtered
            formatted_items = []
            for h in recent:
                # Format timestamp as HH:MM to save tokens
                timestamp_str = ''
                if 'timestamp' in h:
                    from datetime import datetime
                    try:
                        ts = datetime.fromisoformat(h['timestamp'])
                        timestamp_str = ts.strftime('%H:%M')
                    except:
                        timestamp_str = ''
                formatted_items.append(
                    item_tmpl.format(
                        timestamp=timestamp_str,
                        source=h.get("source", ""),
                        text=h.get("text", ""),
                    )
                )
            history_blob = "\n".join(formatted_items).strip()
            if max_chars and len(history_blob) > max_chars:
                history_blob = history_blob[-max_chars:]
            history_header = header_tmpl.format(max_messages=max_messages, history=history_blob)
            if history_header:
                system_prompt = f"{system_prompt}\n\n{history_header}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        resp = self.gemini_llm.invoke(messages)
        content = ""
        if isinstance(resp.content, str):
            content = resp.content
        elif isinstance(resp.content, list):
            for part in resp.content:
                if isinstance(part, str):
                    content += part
                elif isinstance(part, dict) and "content" in part and isinstance(part["content"], str):
                    content += part["content"]
        return content.strip()

if __name__ == "__main__":
    AUTH_KEY = "AUTH_KEY"
    client = GeminiClient()
    client.setAuthKey(AUTH_KEY)
    models = client.getModelList()
    if models:
        print("Available models:", models)
        model = input("Select a model: ")
        client.setModel(model)
        client.updateClient()
        print(client.translate("こんにちは世界", "Japanese", "English"))