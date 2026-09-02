"""OpenAI互換の音声書き起こしAPI (Groq/OpenAI公式/カスタムサーバー) 向けの
認証キー検証・モデル一覧取得ヘルパー。

翻訳側の `models/translation/translation_openai_compatible.py` と同じ
「`client.models.list()` が成功するかどうかでキーの有効性を判定する」
方式 (実際に文字起こしを1回試すより軽量で、起動時の検証に向く)。

「文字起こし可能かどうか」を厳密に判定するのは難しい(実際の音声・
言語次第で結果が変わる)ため、「このキーでモデル一覧を取得できるか」を
可用性の代理指標として使う。
"""

from openai import OpenAI

# OpenAICompatibleTranscriptionProvider を base_url/model の差し替えだけで
# 使い回す3つのユーザー向けエンジン名。transcription_transcriber.py と
# controller.py の双方から参照される唯一の定義元。
TRANSCRIPTION_API_ENGINES = ("Groq_Whisper", "OpenAI_Whisper", "Custom_Whisper")

# Groq/OpenAI公式のモデル一覧には文字起こし以外のモデル(chat/embedding等)も
# 混在するため、モデル名にこれらのキーワードを含むものだけに絞り込む。
# "whisper" は Groq/OpenAI 双方の Whisper 系モデル名 (例: whisper-large-v3,
# whisper-1, distil-whisper-large-v3-en) をカバーし、"transcribe" は
# OpenAI の非Whisper系文字起こしモデル (例: gpt-4o-transcribe,
# gpt-4o-mini-transcribe) をカバーする。カスタムサーバーはどんなモデル名を
# 使っているか分からないため、呼び出し側でこのフィルタを適用しない。
TRANSCRIPTION_MODEL_KEYWORDS = ["whisper", "transcribe"]


def checkTranscriptionApiKey(api_key: str, base_url: str) -> bool:
    """`api_key`/`base_url` の組でモデル一覧が取得できるかどうかを返す。"""
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        client.models.list()
        return True
    except Exception:
        return False


def getAvailableTranscriptionModels(
    api_key: str,
    base_url: str,
    keyword_filter: list[str] | None = None,
) -> list[str]:
    """`api_key`/`base_url` で疎通できるモデル一覧を取得する。

    `keyword_filter` が指定されていれば、モデルID (小文字化) に
    いずれかのキーワードを含むものだけに絞り込む。Groq/OpenAI公式は
    既知の Whisper 系モデル名で絞り込み、カスタムサーバーは
    (どんなモデル名を使っているか分からないため) 絞り込まずに
    全件そのまま返す想定。
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    res = client.models.list()
    models = [m.id for m in res.data]
    if keyword_filter:
        models = [m for m in models if any(kw in m.lower() for kw in keyword_filter)]
    models.sort()
    return models
