"""エクスポートした .onnx を INT8 (静的量子化) にする。CPU 推論を速くするため。

.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_quantize.py `
    -i runs\chatbox_yolox_tiny\chatbox_yolox_tiny.onnx `
    -o src-python\models\ocr\onnx\chatbox_yolox_tiny.onnx --size 736,1280

校正には学習に使った画像を使う (4枚に1枚)。配布物に増える依存は無い。量子化は
ここ(開発マシン)でやる作業で、VRCT 側は今までどおり onnxruntime で読むだけ。

**予測conv以降を fp32 のまま残すのが要点**。グラフ全体を素直に量子化すると
obj/cls のスコアが 0 に潰れて何も検出しなくなる (val20枚で 19/20 → 0/20)。
sigmoid と grid/stride のデコードは uint8 の分解能に耐えない。
逆に Conv だけを量子化すると精度は出るが、conv のたびに fp32 へ戻すので
かえって遅くなる (実測 142ms → 264ms)。

モデルを学習し直したら、この量子化もやり直して tools/eval_bubble_onnx.py で
確認すること。量子化後は conf 0.01 付近の弱い候補が増える (実行時の既定 0.15
では影響しないが、閾値を下げて使うときは効いてくる)。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import (CalibrationDataReader, QuantFormat, QuantType,
                                      quantize_static)
from onnxruntime.quantization.shape_inference import quant_pre_process

ROOT = Path(__file__).resolve().parents[1] / "dataset_annotated"
PAD_COLOR = 114


def preprocess(path: Path, size_h: int, size_w: int) -> np.ndarray:
    """BubbleDetector._letterbox と同じ前処理。校正が本番とずれないように。"""
    frame = cv2.imread(str(path))
    h, w = frame.shape[:2]
    scale = min(size_w / w, size_h / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    canvas = np.full((size_h, size_w, 3), PAD_COLOR, dtype=np.uint8)
    canvas[:nh, :nw] = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
    return np.ascontiguousarray(canvas.transpose(2, 0, 1)[None], dtype=np.float32)


class _Calibration(CalibrationDataReader):
    def __init__(self, paths: list[Path], input_name: str, size_h: int, size_w: int) -> None:
        self._it = iter([{input_name: preprocess(p, size_h, size_w)} for p in paths])

    def get_next(self):
        return next(self._it, None)


def headNodes(model_path: str) -> list[str]:
    """予測conv・sigmoid・デコードのノード名。ここは量子化しない。

    `/head/reg_convs.2/...` のような中間層は量子化してよく、除くのは
    `/head/Sigmoid_4` のような直下のノードと `/head/obj_preds.2/Conv`。
    """
    excluded = []
    for node in onnx.load(model_path).graph.node:
        if not node.name.startswith("/head/"):
            continue
        tail = node.name[len("/head/"):]
        if "/" not in tail or "_preds." in tail:
            excluded.append(node.name)
    return excluded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--size", default="736,1280", help="校正に使う入力サイズ H,W")
    parser.add_argument("--split", default="train")
    parser.add_argument("--every", type=int, default=4, help="校正に使う画像の間引き")
    args = parser.parse_args()

    size_h, size_w = (int(v) for v in args.size.split(","))
    entries = [line.strip() for line in
               (ROOT / f"{args.split}.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    paths = [ROOT / (e[2:] if e.startswith("./") else e) for e in entries][::args.every]

    prepared = f"{args.output}.prepared.onnx"
    quant_pre_process(args.input, prepared, skip_symbolic_shape=True)
    excluded = headNodes(prepared)
    input_name = ort.InferenceSession(
        prepared, providers=["CPUExecutionProvider"]).get_inputs()[0].name

    quantize_static(
        prepared, args.output, _Calibration(paths, input_name, size_h, size_w),
        quant_format=QuantFormat.QDQ, per_channel=True,
        nodes_to_exclude=excluded,
        activation_type=QuantType.QUInt8, weight_type=QuantType.QInt8)
    Path(prepared).unlink(missing_ok=True)
    print(f"wrote {args.output} ({len(paths)} calibration images, "
          f"{len(excluded)} head nodes left in fp32)")


if __name__ == "__main__":
    main()
