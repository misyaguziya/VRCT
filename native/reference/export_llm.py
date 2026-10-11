"""LLM 翻訳エンジンが送る HTTP 要求を、今の Python 版のコードで記録する。

    python native/reference/export_llm.py   ->  native/testdata/llm/llm.json

各エンジンのクライアント (translation_*.py) を、認証 → モデル一覧 → モデル選択 → 翻訳 (履歴あり / なし)
の順に呼び、手順ごとの戻り値と、その間に送った要求 (http_capture.py) を書く。応答は下の responder が返す
決まった値 (Rust 側の模擬サーバーも同じ値を返す)。Gemini の翻訳は gRPC なので別に扱う (ここでは一覧だけ)。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC / "models" / "translation"))
sys.path.insert(0, str(Path(__file__).parent))

from http_capture import capture  # noqa: E402
from translation_languages import loadTranslationLanguages  # noqa: E402

OPENAI_MODELS = [
    {"id": "gpt-4o-mini"}, {"id": "gpt-4o"}, {"id": "whisper-1"}, {"id": "text-embedding-3-small"},
    {"id": "gpt-4o-audio-preview"}, {"id": "ft:gpt-4o-mini:org::abc", "root": "gpt-4o-mini"},
    {"id": "ft:davinci:org::x", "root": "davinci"}, {"id": "dall-e-3"}, {"id": "o1-mini"},
    {"id": "gpt-image-1"}, {"id": "Llama-3.3-70B-Versatile"}, {"id": "Whisper-Large-V3"},
    {"id": "omni-moderation-latest"}, {"id": "bge-rerank"}, {"id": "gpt-4o-search-preview"},
]
OLLAMA_MODELS = [{"name": "llama3.2:latest"}, {"name": "gemma3:4b"}]
GEMINI_PAGES = [
    {"models": [{"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent", "countTokens"]},
                {"name": "models/gemini-2.5-flash-image", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/embedding-001", "supportedGenerationMethods": ["embedContent"]}],
     "nextPageToken": "page2"},
    {"models": [{"name": "models/gemma-3-27b-it", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.5-pro-preview-tts", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["countTokens"]}]},
]
REPLY = "  Hello, nice to meet you!\n"
HISTORY = [
    {"source": "chat", "text": "最初の発言", "timestamp": "2026-10-11T09:05:00"},
    {"source": "ocr", "text": "OCR は対象外", "timestamp": "2026-10-11T09:06:00"},
    {"source": "mic", "text": "Good morning", "timestamp": "2026-10-11T21:30:15.123456"},
    {"source": "speaker", "text": "時刻が読めない", "timestamp": "not a time"},
    {"source": "chat", "text": "時刻なし"},
    {"source": "mic", "text": "{braces} and 'quotes'", "timestamp": "2026-10-11T23:59:59+09:00"},
    {"source": "speaker", "text": "最後の発言", "timestamp": "2026-10-12T00:00:01"},
]


def responder(entry):
    url, method = entry["url"], entry["method"]
    if "invalid" in entry["headers"].get("authorization", "") + entry["headers"].get("x-goog-api-key", ""):
        return 401, {}, {"error": {"message": "Incorrect API key provided", "code": 401}}
    if "generativelanguage.googleapis.com" in url and "/models" in url:
        return 200, {}, GEMINI_PAGES[1 if "pageToken=page2" in url else 0]
    if url.endswith("/auth/key"):
        return 200, {}, {"data": {"label": "test"}}
    if url.endswith("/chat/completions"):
        model = entry["body"]["json"]["model"]
        return 200, {}, {"id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": model,
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": REPLY},
                                      "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
    if url.endswith("/models") and method == "GET":
        return 200, {}, {"object": "list", "data": [{"object": "model", "created": 0, "owned_by": "x", **m}
                                                     for m in OPENAI_MODELS]}
    if url.endswith("/api/tags"):
        return 200, {}, {"models": OLLAMA_MODELS}
    if url.endswith("/api/chat"):
        return 200, {}, {"model": entry["body"]["json"]["model"], "created_at": "2026-10-11T00:00:00Z",
                         "message": {"role": "assistant", "content": REPLY}, "done": True, "done_reason": "stop"}
    if url.rstrip("/").endswith(":11434"):
        return 200, {"content-type": "text/plain"}, "Ollama is running"
    return 404, {}, {"error": "not found"}


def run(name, steps):
    """steps: [(label, callable)] -> {"engine", "steps": [{"step", "result", "requests"}]}"""
    out = []
    for label, call in steps:
        with capture(responder) as records:
            try:
                result = call()
            except Exception as e:  # 記録する (Rust も同じところで失敗するべき)
                result = {"error": type(e).__name__}
        out.append({"step": label, "result": result, "requests": records})
    print(name, [(s["step"], len(s["requests"])) for s in out])
    return {"engine": name, "steps": out}


def key_engine(name, client, key, model):
    def translate(history):
        client.setContextHistory(history)
        return client.translate("こんにちは、はじめまして", "Japanese", "English")
    return run(name, [
        ("setAuthKey_invalid", lambda: client.setAuthKey("invalid-key")),
        ("getModelList_no_key", client.getModelList),
        ("setAuthKey", lambda: client.setAuthKey(key)),
        ("getModelList", client.getModelList),
        ("setModel", lambda: client.setModel(model)),
        ("updateClient", lambda: client.updateClient()),
        ("translate_history", lambda: translate(HISTORY)),
        ("translate_no_history", lambda: translate([])),
        ("getModelList_again", client.getModelList),
    ])


def main():
    loadTranslationLanguages(str(SRC))
    from translation_gemini import GeminiClient
    from translation_groq import GroqClient
    from translation_lmstudio import LMStudioClient
    from translation_ollama import OllamaClient
    from translation_openai import OpenAIClient
    from translation_openai_compatible import OpenAICompatibleClient
    from translation_openrouter import OpenRouterClient
    from translation_plamo import PlamoClient

    engines = [
        key_engine("OpenAI_API", OpenAIClient(root_path=None), "sk-" + "a" * 161, "gpt-4o-mini"),
        key_engine("Groq_API", GroqClient(), "gsk_" + "b" * 40, "Llama-3.3-70B-Versatile"),
        key_engine("OpenRouter_API", OpenRouterClient(), "sk-or-" + "c" * 20, "gpt-4o"),
        key_engine("Plamo_API", PlamoClient(), "d" * 72, "o1-mini"),
        key_engine("OpenAI_Compatible", OpenAICompatibleClient(base_url="http://127.0.0.1:8000/v1/"), "e" * 10,
                   "o1-mini"),
    ]
    lmstudio = LMStudioClient()
    ollama = OllamaClient()
    engines.append(run("LMStudio", [
        ("setBaseURL", lambda: lmstudio.setBaseURL("http://127.0.0.1:1234/v1")),
        ("getModelList", lmstudio.getModelList),
        ("setModel", lambda: lmstudio.setModel("gpt-4o")),
        ("updateClient", lambda: lmstudio.updateClient()),
        ("translate_history", lambda: (lmstudio.setContextHistory(HISTORY),
                                       lmstudio.translate("こんにちは", "Japanese", "English"))[1]),
    ]))
    engines.append(run("Ollama", [
        ("authenticationCheck", ollama.authenticationCheck),
        ("getModelList", ollama.getModelList),
        ("setModel", lambda: ollama.setModel("gemma3:4b")),
        ("updateClient", lambda: ollama.updateClient()),
        ("translate_history", lambda: (ollama.setContextHistory(HISTORY),
                                       ollama.translate("こんにちは", "Japanese", "English"))[1]),
    ]))
    gemini = GeminiClient()
    engines.append(run("Gemini_API", [
        ("setAuthKey_invalid", lambda: gemini.setAuthKey("invalid-key")),
        ("setAuthKey", lambda: gemini.setAuthKey("f" * 39)),
        ("getModelList", gemini.getModelList),
        ("setModel", lambda: gemini.setModel("gemini-2.5-flash")),
        ("updateClient", lambda: gemini.updateClient()),
    ]))
    # 翻訳は gRPC (GenerativeService.GenerateContent)。送る直前の要求を proto3 の JSON (REST の本文と同じ形) で記録する
    from google.ai.generativelanguage_v1beta import GenerateContentRequest, GenerateContentResponse
    from google.ai.generativelanguage_v1beta.services.generative_service import GenerativeServiceClient
    grpc_requests = []

    def generate_content(self, request=None, **kwargs):
        grpc_requests.append({"request": json.loads(GenerateContentRequest.to_json(request)),
                              "metadata": [list(m) for m in kwargs.get("metadata") or []]})
        return GenerateContentResponse({"candidates": [{"content": {"role": "model", "parts": [{"text": REPLY}]},
                                                        "finish_reason": 1}]})

    original = GenerativeServiceClient.generate_content
    GenerativeServiceClient.generate_content = generate_content
    try:
        for label, history in (("translate_history", HISTORY), ("translate_no_history", [])):
            gemini.setContextHistory(history)
            before = len(grpc_requests)
            result = gemini.translate("こんにちは、はじめまして", "Japanese", "English")
            engines[-1]["steps"].append({"step": label, "result": result, "requests": [],
                                         "grpc": grpc_requests[before:]})
    finally:
        GenerativeServiceClient.generate_content = original
    out = ROOT / "native" / "testdata" / "llm" / "llm.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"reply": REPLY, "openai_models": OPENAI_MODELS, "ollama_models": OLLAMA_MODELS,
                               "gemini_pages": GEMINI_PAGES, "history": HISTORY, "engines": engines},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
