"""bat/*.bat と requirements*.txt が ASCII のみ・制御文字なしであることを保証する。

これらのファイルは UTF-8 前提では読まれない。

- cmd.exe は .bat をコンソールの OEM コードページ (日本語環境では CP932) で
  読む。BOM 無し UTF-8 の日本語は CP932 としてデコードできないバイト列になり、
  REM 行が化ける。
- pip-audit の requirements パーサは OS ロケールのコードページでファイルを
  デコードする (docs/backend_review_2026-08-27.md 項目28 で実測済み。
  requirements.txt のコメントに ASCII-only の NOTE がある)。

制御文字を弾くのは別種の事故を止めるため。`tools\\fetch_ocr_models.py` のような
Windows パスを、エスケープを解釈する経路 (Python の文字列リテラル、クォート無し
ヒアドキュメント等) 経由でファイルへ書くと `\\f` が実バイト 0x0C になる。
diff でもエディタでも見た目は変わらないが、cmd からはパスが壊れて実行できない。
57cbd36 の install.bat が実際にこれで動かなくなった (2箇所)。

ガードテストであって振る舞いのテストではない。再発を機械的に止めるのが目的。
"""
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]

# install.bat が pip に渡す2つだけを対象にする。requirements-yolo-train.txt など
# 学習ツール用のファイルは配布物にもインストーラにも関わらないので対象外。
TARGETS = ("bat/*.bat", "requirements.txt", "requirements_cuda.txt")

# 改行だけ許可する。.bat と requirements にタブが必要な場面は無く、タブを許すと
# `\t` を含むパスの取り違え (例: tools\test.py) を見逃す。
ALLOWED_CONTROL_BYTES = frozenset(b"\r\n")


def _targetFiles() -> list[Path]:
    files: list[Path] = []
    for pattern in TARGETS:
        if "*" in pattern:
            files.extend(sorted(REPO_ROOT.glob(pattern)))
        else:
            files.append(REPO_ROOT / pattern)
    return files


class ToolchainFileEncodingTests(unittest.TestCase):
    def test_targets_exist(self) -> None:
        # パターンが空振りして「全部通った」ことにならないようにする
        files = _targetFiles()
        self.assertTrue(files, f"{TARGETS} に一致するファイルが無い")
        for path in files:
            self.assertTrue(path.is_file(), f"{path} が見つからない")

    def test_no_non_ascii_bytes(self) -> None:
        for path in _targetFiles():
            data = path.read_bytes()
            for lineNo, raw in enumerate(data.split(b"\n"), 1):
                offending = [hex(b) for b in raw if b > 0x7F]
                self.assertFalse(
                    offending,
                    f"{path.relative_to(REPO_ROOT)}:{lineNo} に非ASCIIバイト {offending} がある。"
                    " cmd.exe と pip-audit はこのファイルを UTF-8 では読まないので、"
                    " コメントは英語 (ASCII) で書くこと。理由の記録はコミットメッセージへ。"
                    f" 該当行: {raw!r}",
                )

    def test_no_stray_control_bytes(self) -> None:
        for path in _targetFiles():
            data = path.read_bytes()
            for lineNo, raw in enumerate(data.split(b"\n"), 1):
                offending = [
                    hex(b)
                    for b in raw
                    if (b < 0x20 or b == 0x7F) and b not in ALLOWED_CONTROL_BYTES
                ]
                self.assertFalse(
                    offending,
                    f"{path.relative_to(REPO_ROOT)}:{lineNo} に制御文字 {offending} がある。"
                    " Windows パスの `\\f` `\\t` `\\b` 等が、ファイルを書いた経路で"
                    " エスケープとして解釈され実バイトになった可能性が高い"
                    " (57cbd36 の `tools\\fetch_ocr_models.py` が 0x0C で壊れた)。"
                    f" 該当行: {raw!r}",
                )


if __name__ == "__main__":
    unittest.main()
