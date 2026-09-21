# NOTICE

VRCT is distributed under the MIT License (see [`LICENSE`](LICENSE)), **with
the one exception listed below**. The exception applies both to this
repository and to the built application published on GitHub Releases and
BOOTH.

## Exception: the chat-bubble detection model

| | |
|---|---|
| File (repository) | `src-python/models/ocr/onnx/chatbox_yolov8n.onnx` |
| File (built application) | `_internal/ocr_onnx/chatbox_yolov8n.onnx` |
| Copyright | Copyright (c) 2026 misyaguziya |
| License | GNU Affero General Public License v3.0 — [`src-python/models/ocr/onnx/LICENSE.txt`](src-python/models/ocr/onnx/LICENSE.txt) |

This file is **not** covered by the MIT License in `LICENSE`. Every other
file in this repository is.

### Why

The model was fine-tuned from `yolov8n.pt` — the COCO-pretrained weights
published by Ultralytics — using Ultralytics YOLOv8 (`ultralytics==8.3.203`),
which is licensed under AGPL-3.0. Ultralytics states that weights produced
with their software are derivative works subject to AGPL-3.0, and that any
other terms require an Ultralytics Enterprise License. VRCT holds no such
license, so the model is distributed under AGPL-3.0: the project cannot grant
terms broader than the ones it received.

The file was added in commit `51e60af` (2026-09) without this notice, so it
appeared to fall under the repository-wide MIT License. This notice corrects
that.

### If you want to reuse the model

Using this file in your own project obliges you to comply with AGPL-3.0,
including releasing the complete corresponding source of your work under
AGPL-3.0. If you need different terms, train your own detector — the training
procedure is documented in [`docs/ocr_yolo_training.md`](docs/ocr_yolo_training.md)
— or obtain an Enterprise License from Ultralytics. misyaguziya cannot
relicense this file.

## Third-party model weights bundled in the built application

| Component | Version | License |
|---|---|---|
| Ultralytics YOLOv8 `yolov8n.pt` (the base of the model above) | 8.3.203 | AGPL-3.0 |
| RapidOCR and the PP-OCR ONNX models it ships, fetched by `tools/fetch_ocr_models.py` | 3.9.2 | Apache-2.0 |

This table covers bundled **model weights** only. Python package
dependencies are listed in `requirements.txt` / `requirements_cuda.txt` and
carry their own licenses; JavaScript and Rust dependencies are listed in
`package.json` and `src-tauri/Cargo.toml`.
