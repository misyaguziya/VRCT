"""OCRのONNXモデルを配布物へ同梱できるよう、あらかじめ取得する。

python tools/fetch_ocr_models.py

RapidOCRは未取得のモデルを初回使用時にダウンロードする。実行時にネットワークへ
出る経路を作りたくないので、ビルド前にこのスクリプトで全部を rapidocr パッケージ内へ
落としておき、spec の datas でそのまま同梱する (install.bat から呼ばれる)。

取得するのは ocr_languages.py が使う組み合わせだけ。全モデルではない。
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src-python"))

from models.ocr.ocr_languages import SELECTABLE_LANGUAGES, resolveModelSpec  # noqa: E402
from models.ocr import ocr_engine_rapidocr as engine  # noqa: E402


def main() -> None:
    if not engine.isAvailable():
        raise SystemExit("rapidocr is not installed")
    specs = []
    for language in SELECTABLE_LANGUAGES:
        spec = resolveModelSpec(language)
        if spec is not None and spec not in specs:
            specs.append(spec)

    for spec in specs:
        print(f"fetching {spec.label} ...", flush=True)
        if engine.getReader(spec) is None:
            raise SystemExit(f"failed to fetch {spec.label}")

    import rapidocr
    models = Path(rapidocr.__file__).parent / "models"
    files = sorted(models.glob("*.onnx"))
    total = sum(f.stat().st_size for f in files)
    for f in files:
        print(f"  {f.stat().st_size / 1048576:6.1f} MB  {f.name}")
    print(f"{len(files)} models, {total / 1048576:.1f} MB in {models}")


if __name__ == "__main__":
    main()
