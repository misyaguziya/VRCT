# NOTICE

VRCT is distributed under the MIT License (see [`LICENSE`](LICENSE)), **with
the one exception listed below**. The exception applies both to this
repository and to the built application published on GitHub Releases and
BOOTH.

## Exception: the chat-bubble detection model

| | |
|---|---|
| File (repository) | `src-python/models/ocr/onnx/chatbox_yolox_tiny.onnx` |
| File (built application) | `_internal/ocr_onnx/chatbox_yolox_tiny.onnx` |
| Copyright | Copyright (c) 2026 misyaguziya. All rights reserved. |
| License | VRCT Chat-Bubble Detection Model License Agreement — [`LICENSE.txt`](src-python/models/ocr/onnx/LICENSE.txt) (Japanese, authoritative) / [`LICENSE.en.txt`](src-python/models/ocr/onnx/LICENSE.en.txt) (English translation) |

This file is **not** covered by the MIT License in `LICENSE`. Every other
file in this repository is.

### What you may and may not do

You may:

- run the model as part of VRCT on your own machine, and keep backup copies
  for that purpose;
- **run it in a fork of VRCT** while developing, fixing, testing or
  otherwise contributing to VRCT — forks do not have to strip the model out
  to be able to build and run;
- fork or mirror this repository with the model unmodified inside it,
  together with its license and copyright notice;
- redistribute an official VRCT distribution with the model unmodified
  inside it.

You may **not**:

- ship the model inside a fork's own built release (installer, executable
  distribution and the like);
- use the model in software that is not VRCT or a fork of it, or use it
  standalone;
- redistribute it separately, or sell, lend or transfer it;
- create derived models — including by further training, quantizing,
  pruning, converting or distilling it;
- use its outputs to train, evaluate or distil any machine learning model.

The agreement linked above is the authoritative statement; this section is
a summary. If you need terms beyond that, contact the copyright holder.

### Why the model is separate

The model is trained on VRChat screenshots that were collected and
annotated by hand. That dataset, and the weights produced from it, are the
part of VRCT that is not simply source code, and they are kept under the
author's own terms. The intent is narrow: keep the model from being lifted
into unrelated projects. Working on VRCT itself, in a fork, is not what
these terms are aimed at.

The base it is trained from does not constrain this. It is fine-tuned from
`yolox_tiny.pth`, the COCO-pretrained weights published by Megvii under
Apache-2.0, using YOLOX 0.3.0 (also Apache-2.0). Apache-2.0 does not claim
the trained result.

Earlier releases bundled `chatbox_yolov8n.onnx`, fine-tuned from Ultralytics
YOLOv8 weights and therefore distributed under AGPL-3.0. That model has been
replaced and is no longer shipped. Copies already obtained under AGPL-3.0
remain under AGPL-3.0; the change applies from the release that carries
`chatbox_yolox_tiny.onnx` onward. The background is in
[`docs/ocr_model_license.md`](docs/ocr_model_license.md).

### VRCT itself is unaffected

VRCT's source code stays MIT, and creating and distributing a fork is free
under the MIT License. The only consequence for a fork is that it cannot
put the model in its own released build; it can still develop and run with
it. A fork that wants to ship detection can train its own detector — the
procedure, the training configuration and the dataset preparation scripts
are all published in
[`docs/ocr_yolo_training.md`](docs/ocr_yolo_training.md). VRCT also builds
and runs without the model, in which case only chat-bubble detection within
the OCR feature is unavailable.

## Third-party model weights bundled in the built application

| Component | Version | License |
|---|---|---|
| YOLOX `yolox_tiny.pth` (COCO-pretrained base of the model above; not shipped, used only at training time) | 0.1.1rc0 | Apache-2.0 |
| RapidOCR and the PP-OCR ONNX models it ships, fetched by `tools/fetch_ocr_models.py` | 3.9.2 | Apache-2.0 |

This table covers bundled **model weights** only. Python package
dependencies are listed in `requirements.txt` / `requirements_cuda.txt` and
carry their own licenses; JavaScript and Rust dependencies are listed in
`package.json` and `src-tauri/Cargo.toml`.
