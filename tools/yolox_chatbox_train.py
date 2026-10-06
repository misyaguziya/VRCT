"""チャットボックス検出(YOLOX)の学習を Windows 単一GPUで回す。

.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_train.py -c weights\yolox_tiny.pth

.yolox-src\tools\train.py の単一GPU分だけを写したもの。本家をそのまま使わないのは
`configure_nccl()` が Linux 専用のシェルコマンドを呼び、Windows では cmd の
cp932 出力を utf-8 で読んで UnicodeDecodeError で落ちるため。NCCL は複数GPUの
設定なので単一GPUでは何もしなくてよい。clone を書き換えないのは、由来の綺麗さを
保つため(載せ替えの目的がライセンスなので、本家に手を入れない方が説明しやすい)。
"""

from __future__ import annotations

import argparse
import random
import sys
import types
import warnings

# COCOEvaluator は fast_cocoeval (C++拡張) を JIT ビルドしようとする。Windows に
# MSVC がないと CalledProcessError で落ち、本家の ImportError フォールバックに
# 乗らないまま学習ごと止まる。pycocotools の COCOeval を使わせるため、空の
# yolox.layers を先に差しておく (このモジュールを import するのは coco_evaluator だけ)。
sys.modules.setdefault("yolox.layers", types.ModuleType("yolox.layers"))

import torch
import torch.backends.cudnn as cudnn
from yolox.exp import check_exp_value, get_exp
from yolox.utils import configure_module, configure_omp

EXP_FILE = "tools/yolox_chatbox_exp.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--exp_file", default=EXP_FILE)
    parser.add_argument("-c", "--ckpt", default="weights/yolox_tiny.pth",
                        help="COCO事前学習重み (Apache-2.0)")
    parser.add_argument("-b", "--batch-size", type=int, default=8)
    parser.add_argument("--fp16", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("opts", nargs=argparse.REMAINDER, default=None,
                        help="exp の値を上書きする (例: max_epoch 200)")
    args = parser.parse_args()

    # Trainer が参照する属性を train.py と同じ名前で揃える。
    args.experiment_name = None
    args.devices = 1
    args.start_epoch = None
    args.occupy = False
    args.cache = None
    args.logger = "tensorboard"
    args.num_machines = 1
    args.machine_rank = 0
    args.dist_backend = "nccl"
    args.dist_url = None
    args.name = None

    configure_module()
    exp = get_exp(args.exp_file, None)
    exp.merge(args.opts)
    check_exp_value(exp)
    args.experiment_name = exp.exp_name

    if exp.seed is not None:
        random.seed(exp.seed)
        torch.manual_seed(exp.seed)
        cudnn.deterministic = True
        warnings.warn("seeded training enables cudnn.deterministic")

    configure_omp()
    cudnn.benchmark = True

    exp.get_trainer(args).train()


if __name__ == "__main__":
    main()
