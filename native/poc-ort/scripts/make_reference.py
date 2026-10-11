"""PoC 2 の比較用に、現行 Python 実装の出力を JSON に書き出す。

使い方 (PowerShell, リポジトリ直下):
  $env:PYTHONPATH = "tmp\\graphics-site;tmp\\native-site;src-python"
  .venv\\Scripts\\python.exe -X utf8 native\\poc-ort\\scripts\\make_reference.py tmp\\poc-ort <dataset_annotated>

<out>/sapi_speech.wav (16kHz mono int16) を事前に用意しておくこと。PowerShell で:
  Add-Type -AssemblyName System.Speech
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $s.SetOutputToWaveFile("tmp\\poc-ort\\sapi_speech.wav", (New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(
      16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)))
  $s.Speak("Hello, this is a voice activity detection test. The quick brown fox jumps over the lazy dog."); $s.Dispose()
書き出すもの:
  vad_input.wav / vad_py.json      … Silero VAD のフレームごとの発話確率
  yolox_images.txt / yolox_py.json … 吹き出し検出の箱とスコア
  yolox_tensor_<i>.bin             … letterbox 済みテンソル (f32 LE, 1x3xHxW)
  crops/<i>_<j>.png / ocr_py.json  … 検出した吹き出しの切り出しと RapidOCR の結果
  dict_<model>.txt                 … rec モデルのメタデータに埋め込まれた文字辞書
"""

import json
import sys
import time
import wave
from pathlib import Path

import cv2
import numpy as np

OUT = Path(sys.argv[1])
DATASET = Path(sys.argv[2])
SR = 16000


def vad() -> None:
    from models.transcription.audio_vad import FRAME_SAMPLES, SileroFrameProbability

    with wave.open(str(OUT / "sapi_speech.wav")) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (SR, 1, 2)
        speech = np.frombuffer(w.readframes(w.getnframes()), "<i2")
    t = np.arange(SR // 2) / SR
    sine = (0.3 * 32767 * np.sin(2 * np.pi * 440 * t)).astype("<i2")
    silence = np.zeros(SR, "<i2")
    pcm = np.concatenate([silence, sine, silence[: SR // 2], speech, silence])
    with wave.open(str(OUT / "vad_input.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

    prob = SileroFrameProbability()
    # モデルの読み込み (初回呼び出し時) を計測から外す。
    prob(np.zeros(FRAME_SAMPLES, np.float32))
    prob.reset()
    probs = []
    start = time.perf_counter()
    for i in range(len(pcm) // FRAME_SAMPLES):
        frame = pcm[i * FRAME_SAMPLES:(i + 1) * FRAME_SAMPLES].astype(np.float32) / 32768.0
        probs.append(prob(frame))
    elapsed = time.perf_counter() - start
    json.dump({"probs": probs, "elapsed_ms": elapsed * 1000}, open(OUT / "vad_py.json", "w"))
    print(f"vad: {len(probs)} frames, {elapsed * 1000:.1f} ms")


def yolox_and_ocr() -> None:
    from models.ocr import ocr_engine_rapidocr as engine
    from models.ocr.ocr_bubble_detector import BubbleDetector, nonMaxSuppression
    from models.ocr.ocr_languages import resolveModelSpec

    lines = (DATASET / "val_fixed.txt").read_text().split()
    images = [str((DATASET / line).resolve()) for line in lines[::5]]
    (OUT / "yolox_images.txt").write_text("\n".join(images), encoding="utf-8")

    detector = BubbleDetector()
    session = detector.loadModel()
    crops_dir = OUT / "crops"
    crops_dir.mkdir(exist_ok=True)
    yolox = []
    crop_paths = []
    det_ms = 0.0
    for i, path in enumerate(images):
        frame = cv2.imread(path, cv2.IMREAD_COLOR)
        tensor, scale = detector._letterbox(frame)
        tensor.astype("<f4").tofile(OUT / f"yolox_tensor_{i}.bin")
        raw = np.asarray(session.run(None, {detector._input_name: tensor})[0]).reshape(-1, 6)
        start = time.perf_counter()
        results = detector.detect(frame)
        det_ms += (time.perf_counter() - start) * 1000
        # detect() と同じ閾値・NMS を通した、丸め前の箱 (letterbox 座標) とスコア。
        scores = raw[:, 4] * raw[:, 5]
        kept = raw[scores >= detector.confidence]
        kept_scores = scores[scores >= detector.confidence]
        xyxy = np.stack([kept[:, 0] - kept[:, 2] / 2, kept[:, 1] - kept[:, 3] / 2,
                         kept[:, 0] + kept[:, 2] / 2, kept[:, 1] + kept[:, 3] / 2], axis=1)
        order = nonMaxSuppression(xyxy, kept_scores, detector.nms_iou) if len(kept) else []
        yolox.append({
            "path": path,
            "tensor_shape": list(tensor.shape),
            "scale": scale,
            "max_score": float(scores.max()),
            "boxes": [list(bbox) for bbox, _ in results],
            "raw": [{"score": float(kept_scores[k]), "xyxy": xyxy[k].tolist()} for k in order],
        })
        for j, (_, crop) in enumerate(results):
            crop_path = crops_dir / f"{i:02d}_{j}.png"
            cv2.imwrite(str(crop_path), crop)
            crop_paths.append(str(crop_path))
    json.dump({"images": yolox, "elapsed_ms": det_ms}, open(OUT / "yolox_py.json", "w"), indent=1)
    print(f"yolox: {len(images)} images, {len(crop_paths)} crops, {det_ms:.0f} ms")

    # auto = PP-OCRv6 small (多言語), Korean = PP-OCRv5 mobile の言語別 rec。
    for language, name in (("auto", "ocr_py.json"), ("Korean", "ocr_py_korean.json")):
        reader = engine.getReader(resolveModelSpec(language))
        ocr = []
        ocr_ms = 0.0
        for crop_path in crop_paths:
            crop = cv2.imread(crop_path, cv2.IMREAD_COLOR)
            start = time.perf_counter()
            result = reader(crop)
            ocr_ms += (time.perf_counter() - start) * 1000
            ocr.append({
                "path": crop_path,
                "txts": list(result.txts or []),
                "scores": [float(s) for s in (result.scores or [])],
                "boxes": [] if result.boxes is None else np.asarray(result.boxes).tolist(),
            })
        json.dump({"crops": ocr, "elapsed_ms": ocr_ms}, open(OUT / name, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"ocr {language}: {len(crop_paths)} crops, {ocr_ms:.0f} ms")

    # rec 単体の比較用: rapidocr の det+cls を通した行画像と、それを1枚ずつ rec した結果。
    from rapidocr.ch_ppocr_rec import TextRecInput
    reader = engine.getReader(resolveModelSpec("auto"))
    lines_dir = OUT / "lines"
    lines_dir.mkdir(exist_ok=True)
    rec = []
    for crop_path in crop_paths:
        crop = cv2.imread(crop_path, cv2.IMREAD_COLOR)
        img, op_record = reader.preprocess_img(crop)
        try:
            line_imgs, _ = reader.detect_and_crop(img, op_record)
            line_imgs, _ = reader.cls_and_rotate(line_imgs)
        except Exception:
            continue
        for k, line in enumerate(line_imgs):
            line_path = lines_dir / f"{Path(crop_path).stem}_{k}.png"
            cv2.imwrite(str(line_path), line)
            out = reader.text_rec(TextRecInput(img=[line]))
            rec.append({"path": str(line_path), "txt": out.txts[0], "score": float(out.scores[0])})
    json.dump({"lines": rec}, open(OUT / "rec_py.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"rec: {len(rec)} lines")

    import onnxruntime as ort
    for model in ("PP-OCRv6_rec_small", "korean_PP-OCRv5_rec_mobile"):
        model_path = Path(ort.__file__).parent.parent / "rapidocr" / "models" / f"{model}.onnx"
        meta = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"]).get_modelmeta()
        (OUT / f"dict_{model}.txt").write_text(meta.custom_metadata_map["character"], encoding="utf-8")


if __name__ == "__main__":
    vad()
    yolox_and_ocr()
