"""Collector images -> resumable Gemini predictions -> Label Studio review.

No arguments: interactive wizard. CLI: prepare / annotate / export / status / check.
Only annotate sends images to Gemini. API keys are never persisted.
"""

import argparse
from collections import Counter
from email.utils import parsedate_to_datetime
from getpass import getpass
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time

if __package__:
    from . import annotation_job as jobs
else:
    import annotation_job as jobs


class GeminiDetector:
    """Lazy SDK client; automatic retries belong to the outer journal loop."""

    def __init__(self, key: str, model: str):
        from google import genai
        from google.genai import types
        self.types, self.model = types, model
        self.client = genai.Client(api_key=key, vertexai=False, http_options=types.HttpOptions(
            timeout=120_000, retry_options=types.HttpRetryOptions(attempts=1)))

    def __call__(self, data: bytes) -> dict:
        response = self.client.models.generate_content(
            model=self.model,
            contents=[self.types.Part.from_bytes(data=data, mime_type="image/png"), jobs.PROMPT],
            config=self.types.GenerateContentConfig(
                response_mime_type="application/json", response_json_schema=jobs.SCHEMA,
                candidate_count=1, temperature=0, max_output_tokens=8192),
        )
        candidates = response.candidates or []
        finish = candidates[0].finish_reason if candidates else None
        return {"text": response.text or "", "finish_reason": getattr(finish, "value", finish),
                "usage": response.usage_metadata.model_dump(mode="json", exclude_none=True)
                if response.usage_metadata else {}, "model_version": response.model_version}

    def close(self):
        self.client.close()


def retry_delay(exc: Exception, attempt: int) -> float:
    response = getattr(exc, "response", None)
    value = getattr(response, "headers", {}).get("Retry-After") if response is not None else None
    if value:
        try:
            delay = float(value)
        except ValueError:
            try:
                delay = parsedate_to_datetime(value).timestamp() - time.time()
            except (ValueError, TypeError, OverflowError):
                delay = 0
        if math.isfinite(delay) and delay > 0:
            return delay
    return min(60, 2 ** attempt) + random.random()


def annotate(job: Path, *, key: str | None = None, limit: int = 100, interval: float = 6,
             retries: int = 2, retry_failed: bool = False, detector_factory=GeminiDetector,
             sleep=time.sleep, emit=print) -> dict:
    if limit < 0 or not math.isfinite(interval) or interval < 1 or not 0 <= retries <= 5:
        raise ValueError("limit >= 0, interval >= 1 second, retries 0..5 required")
    job = job.resolve()
    with jobs.job_lock(job):
        manifest = jobs.load_job(job)
        jobs.verify_images(job, manifest)
        pending = []
        for entry in manifest["images"]:
            previous = jobs.read_result(job, entry, manifest)
            if previous["status"] == "pending" or (retry_failed and previous["status"] not in jobs.SUCCESS):
                pending.append(entry)
        if limit:
            pending = pending[:limit]
        emit(f"Gemini: model={manifest['model']}, selected={len(pending)}, interval={interval}s")
        if not pending:
            destination = jobs.export_tasks(job, manifest)
            emit(f"Nothing to send. Label Studio: {destination}")
            return status(job, manifest)
        key = key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("Set GEMINI_API_KEY or use the interactive wizard")
        detector = detector_factory(key, manifest["model"])
        calls = 0
        try:
            for index, entry in enumerate(pending, 1):
                data = (job / entry["image"]).read_bytes()
                if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    raise ValueError("Image changed during processing")
                for attempt in range(retries + 1):
                    if calls:
                        sleep(interval)
                    record = {"id": entry["id"], "image_sha256": entry["sha256"],
                              "policy_hash": manifest["policy_hash"], "model": manifest["model"],
                              "started_at": jobs.utc_now(), "status": "unknown"}
                    journal = job / "attempts" / entry["id"] / (jobs.unique_stamp() + ".json")
                    latest = job / "results" / (entry["id"] + ".json")
                    jobs.write_json(journal, record)
                    jobs.write_json(latest, record)
                    calls += 1
                    retry = fatal = False
                    try:
                        raw = detector(data)
                    except Exception as exc:
                        code = getattr(exc, "code", None)
                        # Exception text can contain credentials; retain only type/status.
                        record.update(status="api_error" if isinstance(code, int) else "unknown",
                                      error_type=type(exc).__name__,
                                      http_code=code if isinstance(code, int) else None)
                        retry = code in (429, 500, 502, 503, 504) and attempt < retries
                        fatal = code in (400, 401, 403, 404) or (code == 429 and not retry)
                        delay = retry_delay(exc, attempt + 1) if retry else 0
                    else:
                        record["response"] = raw
                        try:
                            if raw.get("finish_reason") != "STOP":
                                raise ValueError("Response blocked, incomplete or missing STOP")
                            boxes = jobs.validate_boxes(json.loads(raw["text"]))
                            record.update(status="detected" if boxes else "no_detection", boxes=boxes)
                        except (ValueError, TypeError, KeyError) as exc:
                            record.update(status="invalid_response", error_type=type(exc).__name__)
                    record["finished_at"] = jobs.utc_now()
                    jobs.write_json(journal, record)
                    jobs.write_json(latest, record)
                    emit(f"[{index}/{len(pending)}] {entry['id']}: {record['status']}")
                    if retry:
                        emit(f"Temporary API error; retry in at least {delay:.1f}s")
                        sleep(delay)
                        continue
                    break
                if fatal:
                    emit("Stopped on API configuration/quota error. Fix it before --retry-failed.")
                    break
        finally:
            try:
                detector.close()
            finally:
                destination = jobs.export_tasks(job, manifest)
                emit(f"Label Studio: {destination}")
        return status(job, manifest)


def status(job: Path, manifest: dict | None = None) -> dict:
    manifest = manifest or jobs.load_job(job)
    counts = Counter(jobs.read_result(job, e, manifest)["status"] for e in manifest["images"])
    usage = Counter()
    for path in (job / "attempts").glob("*/*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        for field, value in record.get("response", {}).get("usage", {}).items():
            if field.endswith("token_count") and type(value) is int:
                usage[field] += value
    return {"images": len(manifest["images"]), "model": manifest["model"],
            "counts": dict(counts), "reported_usage": dict(usage)}


def base_directory() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


def wizard() -> int:
    print("VRCT Gemini Annotator\n画像一式から作業フォルダを作り、Geminiで仮ラベルを作成します。")
    print("再開する場合は、前回の作業フォルダ（manifest.jsonがある場所）を指定してください。")
    print("中止はCtrl+C。APIキーは保存しません。")
    entered = input("画像一式または作業フォルダのパス: ").strip().strip('"')
    if not entered:
        raise ValueError("画像または作業フォルダのパスを入力してください")
    root = Path(entered).resolve()
    if not (root / "manifest.json").is_file():
        limit = int(input("抽出枚数 [100 / 0=全件]: ").strip() or "100")
        job = base_directory() / "annotation_jobs" / jobs.unique_stamp()
        manifest = jobs.prepare(root, job, limit=limit)
        print(f"準備完了: {len(manifest['images'])}/{manifest['available_images']}枚\n{job}")
    else:
        job = root
    with jobs.job_lock(job):
        manifest = jobs.load_job(job)
        destination = jobs.export_tasks(job, manifest)
        summary = status(job, manifest)
    print(json.dumps(summary, ensure_ascii=False))
    print(f"Label Studio用出力: {destination}")
    action = input("1=Gemini処理（未処理のみ） / 2=失敗・結果不明も再試行 / Enter=準備だけで終了: ").strip()
    if action not in ("1", "2"):
        return 0
    print(f"これから対象画像をGemini APIへ送信します。モデル: {manifest['model']}")
    key = os.environ.get("GEMINI_API_KEY") or getpass("Gemini APIキー（非表示）: ")
    summary = annotate(job, key=key, limit=0, retry_failed=action == "2")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if set(summary["counts"]) <= jobs.SUCCESS else 2


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        if not sys.stdin.isatty():
            raise ValueError("Use prepare / annotate / export / status in a non-interactive terminal")
        return wizard()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Offline: check packaged Gemini SDK without sending requests")
    prepare = commands.add_parser("prepare", help="Offline: snapshot collector PNG/JSON pairs")
    prepare.add_argument("input", type=Path)
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--limit", type=int, default=100, help="Sample size; 0=all")
    prepare.add_argument("--seed", type=int, default=42)
    prepare.add_argument("--model", default=jobs.DEFAULT_MODEL)
    for name in ("annotate", "export", "status"):
        command = commands.add_parser(name)
        command.add_argument("job", type=Path)
        if name == "annotate":
            command.add_argument("--limit", type=int, default=100, help="Images this run; 0=all pending")
            command.add_argument("--interval", type=float, default=6)
            command.add_argument("--retries", type=int, default=2)
            command.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "check":
        detector = GeminiDetector("offline-check-not-a-real-key", jobs.DEFAULT_MODEL)
        try:
            detector.types.GenerateContentConfig(response_mime_type="application/json",
                                                  response_json_schema=jobs.SCHEMA)
        finally:
            detector.close()
        print("Gemini SDK and schema: OK (no request sent)")
        return 0
    if args.command == "prepare":
        manifest = jobs.prepare(args.input, args.out, limit=args.limit, seed=args.seed, model=args.model)
        with jobs.job_lock(args.out):
            destination = jobs.export_tasks(args.out, manifest)
        print(f"Prepared {len(manifest['images'])}/{manifest['available_images']} images: {args.out.resolve()}")
        print(f"Label Studio: {destination}")
        return 0
    if args.command == "annotate":
        summary = annotate(args.job, limit=args.limit, interval=args.interval,
                           retries=args.retries, retry_failed=args.retry_failed)
    else:
        with jobs.job_lock(args.job):
            manifest = jobs.load_job(args.job)
            if args.command == "export":
                print(jobs.export_tasks(args.job, manifest))
            summary = status(args.job, manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if args.command == "annotate" and set(summary["counts"]) - jobs.SUCCESS else 0


def entrypoint() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    try:
        return main()
    except KeyboardInterrupt:
        print("中断しました。保存済みの結果は再開時に使用します。")
        return 130
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", flush=True)
        return 1
    finally:
        if getattr(sys, "frozen", False) and len(sys.argv) == 1 and sys.stdin.isatty():
            try:
                input("Enterで閉じます...")
            except (EOFError, KeyboardInterrupt):
                pass


if __name__ == "__main__":
    raise SystemExit(entrypoint())
