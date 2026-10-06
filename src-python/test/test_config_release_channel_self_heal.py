"""SELECTED_RELEASE_CHANNEL の起動時自己修復に関するテスト。

対象の欠陥:
  UpdateModal は「チャンネルを切り替える」→「インストーラを起動して即
  VRCTを終了する」という順で処理する。config.SELECTED_RELEASE_CHANNEL は
  ManagedProperty (変更のたびにconfig.jsonへ保存) のため、ユーザーが
  インストーラ側をキャンセルしても、config.json には新チャンネルが
  書き込まれたまま残ってしまう(実際にインストールされているのは元の
  バージョンのまま)。次回起動時、UIは「まだインストールしていない
  チャンネル」を現在のチャンネルとして表示してしまっていた。

  修正: load_config() が、config.json から読み込んだ値を無条件に信用する
  のではなく、起動のたびに実際に動いている VERSION から機械的に
  再判定して上書きする(NSISインストーラの.onInitが${VERSION}の
  "-beta"/"-rc"サフィックスから同じ判定をしているのと同じルール)。
  UI経由の明示的な変更(setSelectedReleaseChannel)自体は今まで通り
  可能で、これは「起動時だけは実態を優先する」上書きにすぎない。
"""

import json
import tempfile
import unittest
from pathlib import Path

from config import Config


def _make_isolated_config(version: str) -> Config:
    """シングルトンキャッシュ(Config.__new__)を経由しない、独立した
    Config インスタンスを作る。object.__new__ で Config.__new__ の
    シングルトン取得ロジックを迂回する。"""
    instance = object.__new__(Config)
    instance.init_config()
    instance._VERSION = version
    return instance


class ReleaseChannelDerivationTests(unittest.TestCase):
    """Config._channelForVersion() 単体のテスト。"""

    def test_plain_version_is_stable(self) -> None:
        self.assertEqual(Config._channelForVersion("3.5.1"), "stable")

    def test_beta_suffix_is_beta(self) -> None:
        self.assertEqual(Config._channelForVersion("3.5.1-beta.1"), "beta")

    def test_rc_suffix_is_beta(self) -> None:
        self.assertEqual(Config._channelForVersion("3.5.1-rc.2"), "beta")


class LoadConfigSelfHealsReleaseChannelTests(unittest.TestCase):
    """load_config() が SELECTED_RELEASE_CHANNEL を VERSION から
    再同期することの結合テスト(実際に一時ファイル経由でconfig.jsonの
    読み書きを行う)。"""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._config_path = Path(self._tmpdir.name) / "config.json"

    def _load_with_persisted_channel_and_version(
        self, persisted_channel: str, version: str
    ) -> Config:
        # 「前回起動時にUIでチャンネルを切り替えたが、インストーラを
        # キャンセルした」状態を模す: config.jsonには新チャンネルが
        # 書かれているが、VERSIONは元のまま。
        self._config_path.write_text(
            json.dumps({"SELECTED_RELEASE_CHANNEL": persisted_channel}),
            encoding="utf-8",
        )

        instance = _make_isolated_config(version)
        instance._PATH_CONFIG = str(self._config_path)
        instance.load_config()
        self.addCleanup(self._cancel_pending_timer, instance)
        return instance

    @staticmethod
    def _cancel_pending_timer(instance: Config) -> None:
        timer = getattr(instance, "_timer", None)
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass

    def test_stale_beta_selection_is_corrected_back_to_stable(self) -> None:
        # config.jsonは「beta」を選んだままだが、実際に動いているのは
        # 素のstableバージョン(=インストーラをキャンセルした状況)。
        instance = self._load_with_persisted_channel_and_version(
            persisted_channel="beta", version="3.5.1",
        )
        self.assertEqual(instance.SELECTED_RELEASE_CHANNEL, "stable")

    def test_stale_stable_selection_is_corrected_to_beta_when_actually_running_beta(
        self,
    ) -> None:
        # 逆方向: config.jsonは古い「stable」のままだが、実際にはbeta版の
        # インストールが完了している。
        instance = self._load_with_persisted_channel_and_version(
            persisted_channel="stable", version="3.6.0-beta.1",
        )
        self.assertEqual(instance.SELECTED_RELEASE_CHANNEL, "beta")

    def test_corrected_value_is_persisted_back_to_disk(self) -> None:
        instance = self._load_with_persisted_channel_and_version(
            persisted_channel="beta", version="3.5.1",
        )
        saved = json.loads(self._config_path.read_text(encoding="utf-8"))
        self.assertEqual(saved.get("SELECTED_RELEASE_CHANNEL"), "stable")

    def test_ui_can_still_change_it_after_startup(self) -> None:
        # 起動時の上書きは「起動時だけ」であり、その後のUI経由の変更
        # (setSelectedReleaseChannel)は今まで通り可能なこと。
        instance = self._load_with_persisted_channel_and_version(
            persisted_channel="stable", version="3.5.1",
        )
        instance.SELECTED_RELEASE_CHANNEL = "beta"
        self.assertEqual(instance.SELECTED_RELEASE_CHANNEL, "beta")


if __name__ == "__main__":
    unittest.main()
