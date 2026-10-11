"""Python 版が送る HTTP 要求を、送信の直前 (httpx / requests / urllib の送信部分) で横取りして記録する。

ネットワークには出ず、responder が返す応答 (status, headers, body) をそのまま返す。記録は
{"method", "url", "headers" (名前は小文字), "body"}。body は JSON なら {"json"}、multipart/form-data なら
パートの並び {"multipart": [{"name", "filename", "content_type", "text" | "base64"}]} (境界文字列は比べない
ので content-type からも外す)、それ以外は {"text"} (UTF-8 として読めなければ {"base64"})。Rust 側は同じ
応答を返す模擬サーバーへ要求を送り、記録を比べる。

    with capture(responder) as records:
        ...  # Python のコードを呼ぶ
"""

import base64
import contextlib
import email.parser
import email.policy
import io
import json
import urllib.error
import urllib.request

import httpx
import requests


def _data(raw):
    try:
        return {"text": bytes(raw).decode("utf-8")}
    except UnicodeDecodeError:
        return {"base64": base64.b64encode(raw).decode()}


def _multipart(raw, content_type):
    message = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
        b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + bytes(raw))
    parts = []
    for part in message.iter_parts():
        parts.append({"name": part.get_param("name", header="content-disposition"),
                      "filename": part.get_filename(),
                      "content_type": part.get_content_type() if part.get("content-type") else None,
                      **_data(part.get_payload(decode=True))})
    return {"multipart": parts}


def _body(raw, content_type):
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, (bytes, bytearray)):
        raw = b"".join(raw)
    if not raw:
        return None
    if content_type.startswith("multipart/form-data"):
        return _multipart(raw, content_type)
    try:
        text = bytes(raw).decode("utf-8")
    except UnicodeDecodeError:
        return {"base64": base64.b64encode(raw).decode()}
    try:
        return {"json": json.loads(text)}
    except ValueError:
        return {"text": text}


def _record(records, method, url, headers, raw):
    headers = {k.lower(): v for k, v in headers.items()}
    content_type = headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        headers["content-type"] = "multipart/form-data"
    entry = {"method": method, "url": str(url), "headers": headers, "body": _body(raw, content_type)}
    records.append(entry)
    return entry


def _encode(body):
    if body is None:
        return b""
    if isinstance(body, (dict, list)):
        return json.dumps(body).encode()
    return body if isinstance(body, bytes) else str(body).encode()


class _UrllibResponse(io.BytesIO):
    def __init__(self, status, headers, content, url):
        super().__init__(content)
        self.status = status
        self.headers = headers
        self.url = url

    def getcode(self):
        return self.status

    def geturl(self):
        return self.url


@contextlib.contextmanager
def capture(responder):
    """responder(entry) -> (status, headers dict, body: dict/list/bytes/str/None)"""
    records = []
    original_httpx = httpx.HTTPTransport.handle_request
    original_httpx_async = httpx.AsyncHTTPTransport.handle_async_request
    original_requests = requests.adapters.HTTPAdapter.send
    original_urllib = urllib.request.OpenerDirector.open

    def handle_request(self, request):
        entry = _record(records, request.method, request.url, request.headers, request.read())
        status, headers, body = responder(entry)
        headers = {"content-type": "application/json", **(headers or {})}
        return httpx.Response(status, headers=headers, content=_encode(body), request=request)

    async def handle_async_request(self, request):
        entry = _record(records, request.method, request.url, request.headers, await request.aread())
        status, headers, body = responder(entry)
        headers = {"content-type": "application/json", **(headers or {})}
        return httpx.Response(status, headers=headers, content=_encode(body), request=request)

    def send(self, request, **kwargs):
        entry = _record(records, request.method, request.url, request.headers, request.body)
        status, headers, body = responder(entry)
        response = requests.Response()
        response.status_code = status
        response.headers = requests.structures.CaseInsensitiveDict(
            {"content-type": "application/json", **(headers or {})})
        response._content = _encode(body)
        response._content_consumed = True
        response.encoding = "utf-8"
        response.url = request.url
        response.request = request
        return response

    def urllib_open(self, fullurl, data=None, timeout=None):
        request = fullurl if isinstance(fullurl, urllib.request.Request) else urllib.request.Request(fullurl, data)
        headers = dict(request.header_items())
        method = request.get_method()
        entry = _record(records, method, request.full_url, headers, request.data)
        status, response_headers, body = responder(entry)
        if status >= 400:
            raise urllib.error.HTTPError(request.full_url, status, "error", response_headers or {},
                                         io.BytesIO(_encode(body)))
        return _UrllibResponse(status, response_headers or {}, _encode(body), request.full_url)

    httpx.HTTPTransport.handle_request = handle_request
    httpx.AsyncHTTPTransport.handle_async_request = handle_async_request
    requests.adapters.HTTPAdapter.send = send
    urllib.request.OpenerDirector.open = urllib_open
    try:
        yield records
    finally:
        httpx.HTTPTransport.handle_request = original_httpx
        httpx.AsyncHTTPTransport.handle_async_request = original_httpx_async
        requests.adapters.HTTPAdapter.send = original_requests
        urllib.request.OpenerDirector.open = original_urllib
