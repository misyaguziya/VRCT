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

from typing import Optional

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

    DeepgramProvider が候補言語1つに確定している場合に明示的な
    `language=` コードを解決する (`resolveDeepgramLanguageCode()`) のに
    使うほか、UI側で「このモデルはどの言語に対応しているか」を利用者に
    示すためにも使える (Deepgramの対応言語はモデルごとに異なるため)。

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


def resolveDeepgramLanguageCode(language: str, country: str, model_languages: list) -> Optional[str]:
    """VRCT の (Language, Country) に対して、モデルが実際に対応言語として
    申告しているコードのうち、最も精度の高い一致を返す。

    Deepgram のモデルは "en"/"en-AU"/"en-GB"/"en-US" のように、ベース
    コード+地域サフィックスの形で国ごとに対応言語を区別していることが
    多い (`/v1/models` の実データで確認済み)。これを活かすため2段階で
    照合する:

    1. 既存の "Google" 列 (地域付きコード、例: "en-AU") がモデルの対応
       言語一覧に完全一致すればそれを返す (GoogleのコードはDeepgramと
       同じBCP-47的な地域付き表記に近く、国レベルで正確な一致が期待
       できるため)。
    2. 完全一致しなければ、"Whisper" 列のベースコード (地域サフィックス
       無し) が一致するコードを、モデルが実際に申告している表記のまま
       返す (例: モデルが地域を区別せず "en" のみ申告している場合、
       "English"/どの国 に対しても "en" を返す)。Googleの表記が
       Deepgramと食い違う言語 (中国語="cmn-Hans-CN"、ヘブライ語="iw-IL"
       等) でも、少なくとも言語レベルの一致は取りこぼさない。

    どちらにも一致しなければ None を返す (呼び出し元は
    `detect_language=true` による自動検出にフォールバックする想定)。
    "multi" (Deepgramの一部モデルが多言語対応であることを表す特殊値)
    しか無い場合も、特定の言語コードとして渡す意味が無いため None を
    返す。

    どのモデルがどの言語に対応しているかという情報自体はDeepgram自身の
    API応答 (`/v1/models`) から都度取得するため、VRCT側で対応言語の
    一覧を静的に保守する必要が無い (新しい言語がDeepgram側に追加されても
    コード変更なしに追従する)。
    """
    try:
        entry = transcription_lang[language][country]
    except KeyError:
        return None

    normalized_to_original = {}
    for code in model_languages:
        if code:
            normalized_to_original.setdefault(code.lower(), code)

    if not normalized_to_original or "multi" in normalized_to_original:
        return None

    google_code = entry.get("Google")
    if google_code and google_code.lower() in normalized_to_original:
        return normalized_to_original[google_code.lower()]

    whisper_code = entry.get("Whisper")
    if not whisper_code:
        return None
    base_code = _base_language_code(whisper_code)
    for normalized_code, original_code in normalized_to_original.items():
        if _base_language_code(normalized_code) == base_code:
            return original_code

    return None


def isLanguageSupportedByDeepgramModel(language: str, country: str, model_languages: list) -> bool:
    """VRCT の (Language, Country) が、あるDeepgramモデルの対応言語一覧
    (`getAvailableDeepgramModelsDetailed()` が返す `languages`) に含まれる
    かどうかを動的に判定する (UIの言語リスト絞り込み用)。

    "multi" は「どの言語にも対応しうる」ことを表す特殊値なので、
    (`resolveDeepgramLanguageCode()` が具体的なコードを返せなくても)
    対応ありとみなす。
    """
    model_codes_normalized = {code.lower() for code in model_languages if code}
    if "multi" in model_codes_normalized:
        return True
    return resolveDeepgramLanguageCode(language, country, model_languages) is not None
