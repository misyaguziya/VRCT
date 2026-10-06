"""チャットボックス検出(YOLOX-Nano)の学習設定。Tiny との比較用。

.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_train.py \
    -f tools\yolox_chatbox_exp_nano.py -c weights\yolox_nano.pth

Tiny (5.06M) との違いは width と depthwise だけ。パラメータは 0.91M まで減り、
ONNX も 20MB から 4MB 程度になる。CPU 推論が軽くなるぶん、小さい吹き出しの
取りこぼしが増えないかを実測で見るために用意している。
"""

import os
import sys

import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from yolox_chatbox_exp import Exp as ChatboxExp  # noqa: E402


class Exp(ChatboxExp):
    def __init__(self):
        super().__init__()
        self.width = 0.25
        self.exp_name = "chatbox_yolox_nano"

    def get_model(self, sublinear=False):
        # exps/default/yolox_nano.py と同じ。Nano は depthwise=True が本体の違い。
        from yolox.models import YOLOX, YOLOPAFPN, YOLOXHead

        def init_yolo(M):
            for m in M.modules():
                if isinstance(m, nn.BatchNorm2d):
                    m.eps = 1e-3
                    m.momentum = 0.03

        if getattr(self, "model", None) is None:
            in_channels = [256, 512, 1024]
            backbone = YOLOPAFPN(self.depth, self.width, in_channels=in_channels,
                                 act=self.act, depthwise=True)
            head = YOLOXHead(self.num_classes, self.width, in_channels=in_channels,
                             act=self.act, depthwise=True)
            self.model = YOLOX(backbone, head)

        self.model.apply(init_yolo)
        self.model.head.initialize_biases(1e-2)
        self.model.train()
        return self.model
