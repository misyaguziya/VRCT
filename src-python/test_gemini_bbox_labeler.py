"""Offline tests only: synthetic collector images, fake responses and HTTP MockTransport."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import xml.etree.ElementTree as ET

from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import annotation_job as jobs  # noqa: E402
from tools import gemini_bbox_labeler as app  # noqa: E402


def capture(root, session="日本語", name="same", size=(200, 100)):
    folder = root / session / "unlabeled"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    Image.new("RGB", size, "navy").save(path)
    jobs.write_json(path.with_suffix(".json"), {
        "image": path.name, "width": size[0], "height": size[1],
        "label": "unlabeled", "session": session, "run_id": session, "backend": "openvr_d3d11"})
    return path


def prepared(tmp_path, count=1):
    source = tmp_path / "収集 画像"
    for i in range(count):
        capture(source, name=str(i))
    job = tmp_path / "作業 job"
    manifest = jobs.prepare(source, job, limit=0)
    return job, manifest


def box(coords=(100, 200, 400, 600)):
    return {"box_2d": list(coords), "label": "chat_box"}


def response(boxes=None, **kwargs):
    return {"text": json.dumps([box()] if boxes is None else boxes), "finish_reason": "STOP",
            "usage": {"prompt_token_count": 10, "candidates_token_count": 5}, **kwargs}


def run(job, outputs, **kwargs):
    detector = Mock(side_effect=outputs)
    summary = app.annotate(job, key="test-not-a-real-key", detector_factory=Mock(return_value=detector),
                           sleep=Mock(), emit=Mock(), **kwargs)
    return summary, detector


def test_prepare_preserves_sources_and_disambiguates_same_names(tmp_path):
    source = tmp_path / "input"
    paths = [capture(source, session=s) for s in ("A", "B")]
    before = [jobs.file_hash(p) for p in paths]
    job = tmp_path / "job"
    manifest = jobs.prepare(source, job)
    assert [jobs.file_hash(p) for p in paths] == before
    assert len({e["id"] for e in manifest["images"]}) == 2
    assert {e["source"] for e in manifest["images"]} == {"A/unlabeled/same.png", "B/unlabeled/same.png"}
    jobs.verify_images(job, manifest)
    with pytest.raises(ValueError, match="NEW"):
        jobs.prepare(source, job)
    with pytest.raises(ValueError, match="outside"):
        jobs.prepare(source, source / "job")


def test_sampling_is_seeded_and_spreads_across_runs(tmp_path):
    root = tmp_path / "input"
    for session in ("A", "B", "C"):
        for i in range(5):
            capture(root, session, str(i))
    candidates = jobs.discover(root)
    a = jobs.select_images(candidates, 3, 42)
    assert a == jobs.select_images(candidates, 3, 42)
    assert {data["session"] for _, data in a} == {"A", "B", "C"}
    assert len(jobs.select_images(candidates, 0, 42)) == 15


@pytest.mark.parametrize("damage", ["missing", "dimensions", "invalid_png", "image_name"])
def test_invalid_capture_never_publishes_job(tmp_path, damage):
    root = tmp_path / "input"
    image = capture(root)
    sidecar = image.with_suffix(".json")
    if damage == "missing":
        sidecar.unlink()
    elif damage == "invalid_png":
        image.write_bytes(b"not png")
    else:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        data["width" if damage == "dimensions" else "image"] = 123 if damage == "dimensions" else "other.png"
        jobs.write_json(sidecar, data)
    with pytest.raises((ValueError, OSError)):
        jobs.prepare(root, tmp_path / "job")
    assert not (tmp_path / "job").exists()
    assert not list(tmp_path.glob(".prepare_*"))


@pytest.mark.parametrize("value", [None, {}, [box((1, 2, 1, 4))], [box((-1, 0, 500, 500))],
                                  [box((0, 0, 1001, 1000))], [box((800, 900, 100, 200))],
                                  [box((True, 0, 100, 100))], [box((0.1, 0, 100, 100))],
                                  [box((0, 1, 2))], [{"box_2d": [0, 0, 2, 2], "label": "nameplate"}],
                                  [box(), box()], [box(), {"unexpected": 1}]])
def test_bad_boxes_rejected_without_partial_labels(value):
    with pytest.raises(ValueError):
        jobs.validate_boxes(value)


def test_multibox_empty_invalid_and_predictions_contract(tmp_path):
    job, manifest = prepared(tmp_path, 3)
    summary, detector = run(job, [response([box(), box((500, 100, 900, 300))]),
                                  response([]), response(text="```json\n[]\n```")])
    assert summary["counts"] == {"detected": 1, "no_detection": 1, "invalid_response": 1}
    assert summary["reported_usage"]["prompt_token_count"] == 30
    detector.close.assert_called_once()
    export = next((job / "exports").iterdir())
    tasks = json.loads((export / "tasks.json").read_text(encoding="utf-8"))
    assert all("annotations" not in task for task in tasks)
    regions = tasks[0]["predictions"][0]["result"]
    assert len(regions) == 2
    assert regions[0]["value"] == {"x": 20, "y": 10, "width": 40, "height": 30,
                                    "rotation": 0, "rectanglelabels": ["chat_box"]}
    assert regions[0]["original_width"] == 200 and regions[0]["original_height"] == 100
    assert tasks[1]["predictions"][0]["result"] == []
    assert "predictions" not in tasks[2]
    config = ET.fromstring((export / "label_config.xml").read_text())
    assert config.find("RectangleLabels").get("name") == regions[0]["from_name"]
    assert config.find("Image").get("name") == regions[0]["to_name"]
    assert len({t["data"]["image_id"] for t in tasks}) == len(manifest["images"])


def test_resume_skips_success_and_requires_explicit_failed_retry(tmp_path):
    job, _ = prepared(tmp_path, 2)
    run(job, [response(), response(text="invalid")])
    summary, detector = run(job, [])
    detector.assert_not_called()
    assert summary["counts"]["invalid_response"] == 1
    summary, detector = run(job, [response([])], retry_failed=True)
    assert detector.call_count == 1
    assert summary["counts"] == {"detected": 1, "no_detection": 1}
    assert len(list((job / "attempts").glob("*/*.json"))) == 3


def test_image_and_policy_changes_stop_before_client_creation(tmp_path):
    job, manifest = prepared(tmp_path)
    factory = Mock()
    (job / manifest["images"][0]["image"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        app.annotate(job, key="test", detector_factory=factory)
    factory.assert_not_called()
    manifest["model"] = "gemini-something-else"
    jobs.write_json(job / "manifest.json", manifest)
    with pytest.raises(ValueError, match="Model/prompt"):
        jobs.load_job(job)


def test_interrupted_call_is_unknown_and_not_automatically_resent(tmp_path):
    job, manifest = prepared(tmp_path)
    detector = Mock(side_effect=KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        app.annotate(job, key="test", detector_factory=Mock(return_value=detector), emit=Mock())
    detector.close.assert_called_once()
    assert jobs.read_result(job, manifest["images"][0], manifest)["status"] == "unknown"
    summary, detector = run(job, [])
    assert summary["counts"] == {"unknown": 1}
    detector.assert_not_called()


def test_retry_after_and_fatal_errors_never_leak_key(tmp_path):
    job, _ = prepared(tmp_path, 2)
    error = RuntimeError("sensitive-fake-key")
    error.code = 429
    error.response = SimpleNamespace(headers={"Retry-After": "7"})
    assert app.retry_delay(error, 1) == 7
    waits = Mock()
    detector = Mock(side_effect=[error, response(), response()])
    result = app.annotate(job, key="sensitive-fake-key", detector_factory=Mock(return_value=detector),
                          sleep=waits, emit=Mock())
    assert result["counts"] == {"detected": 2}
    assert [call.args[0] for call in waits.call_args_list] == [7, 6, 6]
    assert not any("sensitive-fake-key" in p.read_text(encoding="utf-8") for p in job.rglob("*.json"))


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429])
def test_fatal_api_error_stops_remaining_images(tmp_path, code):
    job, _ = prepared(tmp_path, 2)
    error = RuntimeError("do not expose this")
    error.code = code
    result, detector = run(job, [error], retries=0)
    assert detector.call_count == 1
    assert result["counts"] == {"api_error": 1, "pending": 1}


def test_lock_released_after_exception_and_concurrent_access_rejected(tmp_path):
    job, _ = prepared(tmp_path)
    with jobs.job_lock(job):
        with pytest.raises((ValueError, OSError)):
            with jobs.job_lock(job):
                pytest.fail("lock accepted twice")
    with pytest.raises(RuntimeError):
        with jobs.job_lock(job):
            raise RuntimeError("failure")
    with jobs.job_lock(job):
        pass


def test_export_is_additive_and_does_not_modify_human_work(tmp_path):
    job, _ = prepared(tmp_path)
    human = job / "human_annotations.json"
    human.write_text("leave unchanged")
    first = jobs.export_tasks(job)
    before = (first / "tasks.json").read_bytes()
    second = jobs.export_tasks(job)
    assert first != second and (first / "tasks.json").read_bytes() == before
    assert human.read_text() == "leave unchanged"
    assert not (job / "labels").exists()


def test_actual_sdk_request_and_response_using_in_memory_transport(tmp_path):
    import httpx
    from google import genai
    from google.genai import types

    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps([box()])}]},
                            "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 42, "candidatesTokenCount": 15},
            "modelVersion": jobs.DEFAULT_MODEL})

    detector = app.GeminiDetector.__new__(app.GeminiDetector)
    detector.types, detector.model = types, jobs.DEFAULT_MODEL
    detector.client = genai.Client(api_key="local-fake-key", http_options=types.HttpOptions(
        client_args={"transport": httpx.MockTransport(handler)},
        retry_options=types.HttpRetryOptions(attempts=1)))
    try:
        raw = detector(b"synthetic-image-bytes")
    finally:
        detector.close()
    assert raw["finish_reason"] == "STOP" and raw["usage"]["prompt_token_count"] == 42
    assert jobs.validate_boxes(json.loads(raw["text"])) == [box()]
    assert requests[0]["generationConfig"]["responseJsonSchema"] == jobs.SCHEMA
    assert requests[0]["contents"][0]["parts"][0]["inlineData"]["mimeType"] == "image/png"
