"""チャットボックス検出(YOLOX-Tiny)の学習設定。

.\.venv-yolox\Scripts\python.exe .yolox-src\tools\train.py \
    -f tools\yolox_chatbox_exp.py -d 1 -b 8 --fp16 -o -c weights\yolox_tiny.pth

初期値は Megvii が Apache-2.0 で配布する COCO 事前学習重み。Ultralytics の
yolov8n.pt (AGPL-3.0) と違い、成果物のライセンスを自前で決められる。
移行の経緯は docs/ocr_model_license.md を参照。

augmentation は引退した YOLOv8n 側の設定と揃えてある (対応表は
docs/ocr_yolox_migration_2026-09-22.md)。基盤の差だけを比較するため、
train/val の分割も同じものを使う。
"""

import os

from yolox.exp import Exp as MyExp

DATASET_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "dataset_annotated")


class Exp(MyExp):
    def __init__(self):
        super().__init__()
        # YOLOX-Tiny (exps/default/yolox_tiny.py と同じ係数)
        self.depth = 0.33
        self.width = 0.375
        self.num_classes = 1
        self.exp_name = "chatbox_yolox_tiny"
        self.output_dir = "runs"  # YOLOv8n 側の runs/chatbox と並べる

        # ---- データセット ----
        # COCODataset は data_dir/<name>/<file_name> を開く。name を空にして
        # file_name にセッション込みの相対パスを入れるので、画像は複製しない。
        self.data_dir = DATASET_DIR
        self.train_ann = "instances_train_chatbox.json"
        self.val_ann = "instances_val_chatbox.json"
        self.data_num_workers = 2

        # ---- 入力サイズ ----
        # 吹き出しは画面の1%程度しかなく、Tiny既定の416では潰れる。YOLOv8n と同じ1280。
        # FPN の stride は 8/16/32 なので 1280 は割り切れる。
        self.input_size = (1280, 1280)
        self.test_size = (1280, 1280)
        self.multiscale_range = 0  # 固定入力。YOLOv8n 側も imgsz 固定で比較する。

        # ---- augmentation (引退した YOLOv8n 側の設定と対応) ----
        self.mosaic_prob = 0.3      # mosaic: 0.3
        self.enable_mixup = False
        self.mosaic_scale = (0.8, 1.2)  # scale: 0.2
        self.translate = 0.05       # translate: 0.05
        self.degrees = 0.0          # Chat表示は回らない
        self.shear = 0.0
        self.flip_prob = 0.5        # fliplr: 0.5
        self.hsv_prob = 1.0         # hsv_s / hsv_v 相当 (YOLOX は色相も僅かに振る)

        # ---- 学習 ----
        self.max_epoch = 150        # epochs: 150
        self.no_aug_epochs = 20     # close_mosaic: 20
        self.warmup_epochs = 5
        self.eval_interval = 5
        self.seed = 0              # seed: 0 (再現性。cudnn.deterministic も入る)
        self.save_history_ckpt = False

        # ---- 評価 ----
        self.test_conf = 0.01
        self.nmsthre = 0.65

    def get_dataset(self, cache: bool = False, cache_type: str = "ram"):
        from yolox.data import COCODataset, TrainTransform

        return COCODataset(
            data_dir=self.data_dir,
            json_file=self.train_ann,
            name="",
            img_size=self.input_size,
            preproc=TrainTransform(
                max_labels=50, flip_prob=self.flip_prob, hsv_prob=self.hsv_prob),
            cache=cache,
            cache_type=cache_type,
        )

    def get_eval_dataset(self, **kwargs):
        from yolox.data import COCODataset, ValTransform

        return COCODataset(
            data_dir=self.data_dir,
            json_file=self.val_ann,
            name="",
            img_size=self.test_size,
            preproc=ValTransform(legacy=kwargs.get("legacy", False)),
        )
