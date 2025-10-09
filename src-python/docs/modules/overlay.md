# overlay.py — OpenVR オーバーレイ管理

目的: OpenVR を使ったオーバーレイ表示（複数サイズ: small/large）を管理する `Overlay` クラスを提供します。

主要メソッド:
- __init__(self, settings_dict: dict)
- init(self) -> None
- startOverlay(self) -> None
- shutdownOverlay(self) -> None
- reStartOverlay(self) -> None
- updateImage(self, img: PIL.Image.Image, size: str) -> None
- updateOpacity(self, opacity: float, size: str, with_fade: bool = False) -> None
- updateUiScaling(self, ui_scaling: float, size: str) -> None
- updatePosition(self, x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation, tracker, size) -> None
- mainloop(self) -> None  # アニメーション / フェード評価ループ

使用上の注意:
- OpenVR (SteamVR) が稼働していることが前提です。`checkSteamvrRunning()` で `vrmonitor.exe` の存在チェックを行います。
- 例外が発生した場合は `errorLogging()` を呼んでスタックトレースを残します。

短い使用例:

```py
from models.overlay.overlay_image import OverlayImage
from models.overlay.overlay import Overlay
from PIL import Image

settings = {
	"small": {
		"x_pos": 0.0, "y_pos": 0.0, "z_pos": 0.0,
		"x_rotation": 0.0, "y_rotation": 0.0, "z_rotation": 0.0,
		"display_duration": 5, "fadeout_duration": 2,
		"opacity": 1.0, "ui_scaling": 1.0, "tracker": "HMD"
	}
}

overlay_img = OverlayImage()
overlay = Overlay(settings)
overlay.startOverlay()

# wait until initialized
while not overlay.initialized:
		time.sleep(0.5)

# push a simple blank image
overlay.updateImage(Image.new("RGBA", (256, 64), (255,255,255,255)), "small")
```

## モジュール構成（補足）

- overlay.py — OpenVR を使ったオーバーレイ管理。Overlay クラスは複数サイズ（small/large）を扱い、位置/回転/透明度/フェードを制御する。
- overlay_image.py — PIL を使ってオーバーレイに表示する画像を生成（テキストボックス、ログレイアウト、フォント管理）。
- overlay_utils.py — 行列演算や座標変換ユーティリティ。

注意点:
- OpenVR（SteamVR）に依存。SteamVR が動作していることが前提。
- フォントファイルは repo の fonts フォルダか、ランタイム内パスを探索して読み込む。
- 生成画像は RGBA バイト列に変換され `overlay.setOverlayRaw` で渡される。

