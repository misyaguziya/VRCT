"""AMD 検証ツールが OS 名を取り違えないことを確かめる。

`platform.platform()` は Windows 11 でも "Windows-10-10.0.26200-SP0" を返す
(Windows 11 はメジャー 10 のままビルド 22000 以降)。協力者の実機環境を
誤って記録すると、後でドライバや WDDM 由来の差を追うときに前提が崩れる。
実際に「Win11 なのに Windows 10 と出ている」と指摘を受けて直した箇所なので、
判定境界をここで固定する。
"""

import os
import sys
import unittest
from typing import NamedTuple
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "amd_spike"))

import check_amd  # noqa: E402


class _FakeWindowsVersion(NamedTuple):
    major: int
    minor: int
    build: int


class WindowsVersionTest(unittest.TestCase):
    def _name(self, major: int, build: int) -> str:
        with patch.object(sys, "getwindowsversion",
                          lambda: _FakeWindowsVersion(major, 0, build), create=True):
            return check_amd._windowsVersion()

    def test_windows_10_stays_windows_10(self):
        self.assertTrue(self._name(10, 19045).startswith("Windows 10"))

    def test_first_windows_11_build_is_windows_11(self):
        # 22000 が Windows 11 の最初のビルド。境界そのもの。
        self.assertTrue(self._name(10, 22000).startswith("Windows 11"))

    def test_last_windows_10_build_is_not_windows_11(self):
        self.assertTrue(self._name(10, 21999).startswith("Windows 10"))

    def test_current_machine_is_reported_as_windows_11(self):
        # 実機での回帰確認。このリポジトリの開発機は Windows 11。
        self.assertTrue(self._name(10, 26200).startswith("Windows 11"))

    def test_includes_the_build_number(self):
        # ドライバ絡みの問題はビルド番号が無いと絞り込めない。
        self.assertIn("26200", self._name(10, 26200))

    def test_falls_back_instead_of_raising(self):
        def boom():
            raise OSError("no such thing on this platform")

        with patch.object(sys, "getwindowsversion", boom, create=True):
            # 落ちないことだけが要件。何が返るかは環境依存。
            self.assertTrue(check_amd._windowsVersion())


if __name__ == "__main__":
    unittest.main()
