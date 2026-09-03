"""Deepgram の録音済み(バッチ)音声書き起こしREST API向けの
認証キー検証・モデル一覧取得ヘルパー。

Deepgram は OpenAI互換ではない (認証ヘッダーが `Authorization: Token <key>`、
モデル一覧の取得も `/v1/models` という専用のシェイプ) ため、`openai`
パッケージは使わず、既存依存の `requests` で直接叩く (翻訳側の
Ollama/LMStudio 接続 (`models/translation/translation_ollama.py` 等) と
同じ方針で、新規SDK依存を増やさない)。

「文字起こし可能かどうか」を厳密に判定するのは難しいため、OpenAI互換系と
同様「このキーでモデル一覧を取得できるか」を可用性の代理指標として使う。
"""

import requests

from models.transcription.transcription_languages import transcription_lang

_BASE_URL = "https://api.deepgram.com/v1"
# setup.exe ダウンロード等の HTTP 呼び出しで使っている (10, 60) と同じ
# (connect, read) タイムアウト。
_HTTP_TIMEOUT = (10, 60)


def checkDeepgramApiKey(api_key: str) -> bool:
    """`api_key` でモデル一覧が取得できるかどうかを返す。"""
    try:
        response = requests.get(
            f"{_BASE_URL}/models",
            headers={"Authorization": f"Token {api_key}"},
            timeout=_HTTP_TIMEOUT,
        )
        return response.status_code == 200
    except Exception:
        return False


def getAvailableDeepgramModelsDetailed(api_key: str) -> list[dict]:
    """疎通できる音声認識(STT)モデルのうち、録音済み音声(バッチ)に対応する
    ものを、モデル名と対応言語コード一覧つきで返す。

    VRCT の DeepgramProvider は常に `detect_language=true` (自動検出) で
    呼ぶため、コード自体はこの言語コード一覧を参照しないが、UI側で
    「このモデルはどの言語に対応しているか」を利用者に示すために必要
    (Deepgramの対応言語・自動検出可否はモデルごとに異なるため)。

    返り値の例: [{"name": "nova-3", "languages": ["en", "ja", ...]}, ...]
    (`/v1/models` レスポンスの `stt[].batch` フラグで録音済み音声対応の
    ものだけに絞り込む。VRCT の既存パイプラインは「フレーズ確定後に
    まとめて1回で送信する」バッチ型のため、常時ストリーミング専用の
    モデルは選択肢に出す意味が無い。)
    """
    try:
        response = requests.get(
            f"{_BASE_URL}/models",
            headers={"Authorization": f"Token {api_key}"},
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        stt_models = response.json().get("stt", [])
    except Exception:
        return []

    seen = set()
    result = []
    for m in stt_models:
        name = m.get("name")
        if not name or m.get("batch") is not True or name in seen:
            continue
        seen.add(name)
        result.append({"name": name, "languages": list(m.get("languages") or [])})

    result.sort(key=lambda entry: entry["name"])
    return result


def getAvailableDeepgramModels(api_key: str) -> list[str]:
    """疎通できる音声認識(STT)モデルの名前一覧 (録音済み音声対応のみ)。"""
    return [m["name"] for m in getAvailableDeepgramModelsDetailed(api_key)]


def _base_language_code(code: str) -> str:
    """"en-US" -> "en" のように地域サフィックスを落としたベースコード。"""
    return code.split("-")[0].lower()


def isLanguageSupportedByDeepgramModel(language: str, country: str, model_languages: list) -> bool:
    """VRCT の (Language, Country) が、あるDeepgramモデルの対応言語一覧
    (`getAvailableDeepgramModelsDetailed()` が返す `languages`) に含まれる
    かどうかを動的に判定する。

    Deepgram の対応言語コード表を手作業で用意する代わりに、既存の
    "Whisper" 列 (`transcription_lang`) のベースコード (ISO 639-1、地域
    サフィックス無し) を、Deepgramが実際にそのモデルで対応していると
    "自己申告" しているコード一覧と突き合わせる。Deepgramのコードも
    "en"/"en-US" のようにベースコード+任意の地域サフィックスの形を
    取るため、ベースコード同士の一致で判定する。"multi" は Deepgram の
    一部モデルが「多言語対応」を表すのに使う特殊値で、これが含まれる
    場合は原則どの言語も対応とみなす。

    どのモデルがどの言語に対応しているかという情報自体はDeepgram自身の
    API応答 (`/v1/models`) から都度取得するため、VRCT側で対応言語の
    一覧を静的に保守する必要が無い (新しい言語がDeepgram側に追加されても
    コード変更なしに追従する)。
    """
    try:
        whisper_code = transcription_lang[language][country]["Whisper"]
    except KeyError:
        return False

    base_code = _base_language_code(whisper_code)
    model_base_codes = {_base_language_code(code) for code in model_languages if code}
    return "multi" in model_base_codes or base_code in model_base_codes


def getDeepgramSupportedLanguages(model_languages: list) -> dict:
    """`transcription_lang` の全 (Language, Country) について、指定モデルが
    対応しているかどうかを動的に判定した結果を返す。

    返り値の例: {"Japanese": {"Japan": True}, "English": {"United States": True, ...}, ...}
    """
    result: dict = {}
    for language, countries in transcription_lang.items():
        result[language] = {
            country: isLanguageSupportedByDeepgramModel(language, country, model_languages)
            for country in countries
        }
    return result
