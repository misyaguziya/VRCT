"""学習した YOLOX の重みを VRCT が読む .onnx にする。

.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_export.py \
    -c runs\chatbox_yolox_tiny\best_ckpt.pth -o src-python\models\ocr\onnx\chatbox_yolox_tiny.onnx

.yolox-src\tools\export_onnx.py と同じことをするが、次の2点だけ変えてある。

- `torch.load` が torch 2.6 以降の weights_only=True で落ちる。YOLOX の checkpoint は
  best_ap を numpy スカラーで持つため。自分で作った重みなので numpy スカラーだけ
  許可して weights_only=True のまま読む。
- decode を常にグラフへ入れる (`decode_in_inference=True`)。実行時の後処理が
  「閾値 + NMS」だけになり、VRCT 側に grid/stride のデコードを持たずに済む。

NMS はグラフに入らない (YOLOX の実装は torchvision.ops に依存していて ONNX へ
落ちない)。BubbleDetector が numpy で持つ。YOLOv8 のときのように「エクスポート時の
conf が NMS へ焼き込まれて実行時に下げられない」問題は、この形では起きない。
"""

from __future__ import annotations

import argparse

import numpy as np
import torch
from torch import nn
from yolox.exp import get_exp
from yolox.models.network_blocks import SiLU
from yolox.utils import replace_module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--exp_file", default="tools/yolox_chatbox_exp.py")
    parser.add_argument("-c", "--ckpt", default="runs/chatbox_yolox_tiny/best_ckpt.pth")
    parser.add_argument("-o", "--output-name", default="chatbox_yolox_tiny.onnx")
    parser.add_argument("--size", default=None,
                        help="入力サイズ H,W (既定は exp の test_size)。YOLOXは全層が畳み込みで"
                             "余白は左上寄せなので、学習時と同じ縮尺のまま高さだけ詰められる")
    parser.add_argument("--dynamic", action="store_true",
                        help="入力の高さ・幅を可変にする。キャプチャのアスペクト比が"
                             "固定でないので、余白を詰めるならこちら")
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--no-simplify", action="store_true")
    args = parser.parse_args()

    exp = get_exp(args.exp_file, None)
    model = exp.get_model()

    torch.serialization.add_safe_globals(
        [np._core.multiarray.scalar, np.dtype, np.dtypes.Float64DType])
    ckpt = torch.load(args.ckpt, map_location="cpu")
    model.eval()
    model.load_state_dict(ckpt["model"] if "model" in ckpt else ckpt)
    # onnxruntime が読めるよう、nn.SiLU を素の演算で書いた実装に差し替える。
    model = replace_module(model, nn.SiLU, SiLU)
    model.head.decode_in_inference = True

    if args.size:
        exp.test_size = tuple(int(v) for v in args.size.split(","))
    dummy = torch.randn(1, 3, exp.test_size[0], exp.test_size[1])
    torch.onnx.export(
        model, dummy, args.output_name,
        input_names=["images"], output_names=["output"], opset_version=args.opset,
        dynamic_axes={"images": {2: "height", 3: "width"}} if args.dynamic else None)

    if not args.no_simplify:
        import onnx
        from onnxsim import simplify

        simplified, ok = simplify(onnx.load(args.output_name))
        assert ok, "simplified ONNX could not be validated"
        onnx.save(simplified, args.output_name)

    print(f"wrote {args.output_name} (input {exp.test_size}, opset {args.opset})")


if __name__ == "__main__":
    main()
