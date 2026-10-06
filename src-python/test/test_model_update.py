import hashlib
import unittest
from unittest.mock import Mock, patch

from model import Model, SETUP_DOWNLOAD_FAILED, SETUP_LAUNCHED, SETUP_VERIFY_FAILED
from config import config


def _make_download_response(payload: bytes) -> Mock:
    response = Mock()
    response.raise_for_status = Mock()
    response.iter_content.return_value = [payload]
    return response


def _make_json_response(data) -> Mock:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = data
    return response


def _make_text_response(text: str) -> Mock:
    response = Mock()
    response.raise_for_status = Mock()
    response.text = text
    return response


class TestModelUpdate(unittest.TestCase):
    def setUp(self) -> None:
        # _downloadSetup() rejects downloads under 1MB as a likely non-installer
        # payload (e.g. an HTML error page), so every mocked download in this
        # file must clear that threshold.
        self.payload = b"data" * 300_000
        self.actual_sha256 = hashlib.sha256(self.payload).hexdigest()
        # updateSoftware()/updateCudaSoftware() resolve the GitHub Release (to
        # find its ".sha256" sidecar asset) via Model._resolveReleaseForVersion(),
        # which branches on config.SELECTED_RELEASE_CHANNEL: the "stable" path
        # hits config.GITHUB_URL (which every test below mocks), while the "beta"
        # path instead walks Model._fetchGithubReleases() -> config.
        # GITHUB_RELEASES_LIST_URL (which they do not). Left on a "beta" ambient
        # config, release resolution returns None, _fetchExpectedSha256() yields
        # None, and hash verification is silently skipped -- so the
        # sha256-mismatch test would see the installer launched anyway. Pin the
        # channel here so these tests exercise the hash path deterministically
        # regardless of the developer's local config.json (matches
        # test_model_http_timeouts.CheckSoftwareUpdatedTimeoutTests).
        #
        # Patch the ManagedProperty descriptor on the class rather than doing a
        # plain `config.SELECTED_RELEASE_CHANNEL = "stable"`: the latter goes
        # through ManagedProperty.__set__ -> config.saveConfig(), which schedules
        # a debounced rewrite of the developer's real config.json. Swapping the
        # class attribute for a plain string skips the persistence layer
        # entirely, and addCleanup restores the descriptor after the test.
        channel_patcher = patch.object(
            type(config), "SELECTED_RELEASE_CHANNEL", "stable"
        )
        channel_patcher.start()
        self.addCleanup(channel_patcher.stop)

    @patch("model.errorLogging")
    @patch("model.requests_get")
    def test_does_not_run_setup_when_download_keeps_failing(
        self,
        requests_get: Mock,
        error_logging: Mock,
    ) -> None:
        requests_get.side_effect = Exception("network error")

        with patch("model.Popen") as popen:
            Model.updateSoftware()
            Model.updateCudaSoftware()

        popen.assert_not_called()
        # per call: 1 release-resolution attempt (fails, caught inside
        # _resolveReleaseForVersion) + 5 _downloadSetup() retry attempts.
        self.assertEqual(requests_get.call_count, 12)
        self.assertEqual(error_logging.call_count, 12)

    @patch("model.os_exit")
    @patch("model.psutil_Process")
    @patch("model.Popen")
    @patch("model.requests_get")
    def test_falls_back_to_size_check_when_no_sha256_asset_published(
        self,
        requests_get: Mock,
        popen: Mock,
        psutil_process: Mock,
        os_exit: Mock,
    ) -> None:
        # The GitHub release has no ".sha256" sidecar asset (e.g. a release
        # published before this feature existed). Hash verification is
        # skipped and the update proceeds on the size check alone, so old
        # releases stay installable/downgradable.
        def fake_get(url, *args, **kwargs):
            if url == config.GITHUB_URL:
                return _make_json_response({"name": "9.9.9", "assets": []})
            return _make_download_response(self.payload)

        requests_get.side_effect = fake_get

        Model.updateCudaSoftware()

        popen.assert_called_once()
        os_exit.assert_called_once_with(0)

    @patch("model.os_exit")
    @patch("model.psutil_Process")
    @patch("model.Popen")
    @patch("model.requests_get")
    def test_rejects_setup_on_sha256_mismatch(
        self,
        requests_get: Mock,
        popen: Mock,
        psutil_process: Mock,
        os_exit: Mock,
    ) -> None:
        wrong_hash = "0" * 64
        sha_asset_url = "https://example.invalid/VRCT_9.9.9_x64-setup.exe.sha256"

        def fake_get(url, *args, **kwargs):
            if url == config.GITHUB_URL:
                return _make_json_response({
                    "name": "9.9.9",
                    "assets": [{
                        "name": "VRCT_9.9.9_x64-setup.exe.sha256",
                        "browser_download_url": sha_asset_url,
                    }],
                })
            if url == sha_asset_url:
                return _make_text_response(wrong_hash)
            return _make_download_response(self.payload)

        requests_get.side_effect = fake_get

        Model.updateCudaSoftware()

        # A mismatched checksum means the downloaded file cannot be trusted;
        # the installer must never be launched.
        popen.assert_not_called()
        os_exit.assert_not_called()

    @patch("model.os_exit")
    @patch("model.psutil_Process")
    @patch("model.Popen")
    @patch("model.requests_get")
    def test_installs_when_sha256_matches(
        self,
        requests_get: Mock,
        popen: Mock,
        psutil_process: Mock,
        os_exit: Mock,
    ) -> None:
        sha_asset_url = "https://example.invalid/VRCT_9.9.9_x64-setup.exe.sha256"

        def fake_get(url, *args, **kwargs):
            if url == config.GITHUB_URL:
                return _make_json_response({
                    "name": "9.9.9",
                    "assets": [{
                        "name": "VRCT_9.9.9_x64-setup.exe.sha256",
                        "browser_download_url": sha_asset_url,
                    }],
                })
            if url == sha_asset_url:
                return _make_text_response(self.actual_sha256)
            return _make_download_response(self.payload)

        requests_get.side_effect = fake_get

        Model.updateCudaSoftware()

        popen.assert_called_once()
        os_exit.assert_called_once_with(0)

    @patch("model.os_exit")
    @patch("model.psutil_Process")
    @patch("model.Popen")
    @patch("model.requests_get")
    def test_aborts_when_published_sha256_sidecar_cannot_be_fetched(
        self,
        requests_get: Mock,
        popen: Mock,
        psutil_process: Mock,
        os_exit: Mock,
    ) -> None:
        # The release advertises a ".sha256" sidecar, but every attempt to
        # download it fails. This is NOT the same as a release that has no
        # sidecar at all (which may fall back to the size-only check): here a
        # checksum WAS published and we could not obtain it, so tampering
        # cannot be ruled out and the installer must not be launched.
        sha_asset_url = "https://example.invalid/VRCT_9.9.9_x64-setup.exe.sha256"

        def fake_get(url, *args, **kwargs):
            if url == config.GITHUB_URL:
                return _make_json_response({
                    "name": "9.9.9",
                    "assets": [{
                        "name": "VRCT_9.9.9_x64-setup.exe.sha256",
                        "browser_download_url": sha_asset_url,
                    }],
                })
            if url == sha_asset_url:
                raise Exception("sidecar fetch failed")
            return _make_download_response(self.payload)

        requests_get.side_effect = fake_get

        Model.updateCudaSoftware()

        popen.assert_not_called()
        os_exit.assert_not_called()
        # the sidecar fetch is retried, not attempted only once
        sidecar_calls = [
            call for call in requests_get.call_args_list
            if call.args and call.args[0] == sha_asset_url
        ]
        self.assertEqual(len(sidecar_calls), Model._SHA256_SIDECAR_ATTEMPTS)

    @patch("model.os_exit")
    @patch("model.psutil_Process")
    @patch("model.Popen")
    @patch("model.requests_get")
    def test_installs_when_sha256_sidecar_recovers_on_retry(
        self,
        requests_get: Mock,
        popen: Mock,
        psutil_process: Mock,
        os_exit: Mock,
    ) -> None:
        # A transient failure on the tiny ".sha256" request must not sink an
        # otherwise-valid update: the first attempt fails, the retry returns
        # the correct digest, and the install proceeds.
        sha_asset_url = "https://example.invalid/VRCT_9.9.9_x64-setup.exe.sha256"
        sidecar_attempts = {"n": 0}

        def fake_get(url, *args, **kwargs):
            if url == config.GITHUB_URL:
                return _make_json_response({
                    "name": "9.9.9",
                    "assets": [{
                        "name": "VRCT_9.9.9_x64-setup.exe.sha256",
                        "browser_download_url": sha_asset_url,
                    }],
                })
            if url == sha_asset_url:
                sidecar_attempts["n"] += 1
                if sidecar_attempts["n"] == 1:
                    raise Exception("transient sidecar failure")
                return _make_text_response(self.actual_sha256)
            return _make_download_response(self.payload)

        requests_get.side_effect = fake_get

        Model.updateCudaSoftware()

        self.assertEqual(sidecar_attempts["n"], 2)
        popen.assert_called_once()
        os_exit.assert_called_once_with(0)

    @patch("model.os_exit")
    @patch("model.psutil_Process")
    @patch("model.Popen")
    @patch("model.requests_get")
    def test_quits_app_after_launching_setup(
        self,
        requests_get: Mock,
        popen: Mock,
        psutil_process: Mock,
        os_exit: Mock,
    ) -> None:
        # A single generic mocked response for every call: its .json() is an
        # unconfigured Mock (not a dict), so release resolution yields no
        # usable release object and hash verification cleanly falls back to
        # the size check, matching pre-item-13 behavior for this happy path.
        requests_get.return_value = _make_download_response(self.payload)

        Model.updateCudaSoftware()

        popen.assert_called_once_with(
            [
                "VRCT_setup.exe",
                "/EDITION=gpu",
                f"/UILANG={config.UI_LANGUAGE}",
                f"/CHANNEL={config.SELECTED_RELEASE_CHANNEL}",
            ],
            cwd=config.PATH_LOCAL,
        )
        psutil_process.return_value.terminate.assert_called_once()
        os_exit.assert_called_once_with(0)


class TestPinnedVersionDownload(unittest.TestCase):
    """バージョンを指定した更新 (旧版への戻しなど) は、その版の setup.exe を取る。

    main は常に最新版なので、そこから取った setup.exe を指定版の .sha256 で
    検証すると、最新版以外では必ず不一致になって更新が中止された (2026-10-06、
    beta.2 から beta.1 を選んだとき)。
    """

    BETA_MAIN = "https://huggingface.co/ms-software/VRCT-beta/resolve/main/VRCT_setup.exe"
    STABLE_MAIN = "https://huggingface.co/ms-software/VRCT/resolve/main/VRCT_setup.exe"

    def setUp(self) -> None:
        self.payload = b"data" * 300_000
        self.sha256 = hashlib.sha256(self.payload).hexdigest()
        # 現在のチャンネル (stable) と、指定する版 (beta) が違う場合を使う
        channel_patcher = patch.object(type(config), "SELECTED_RELEASE_CHANNEL", "stable")
        channel_patcher.start()
        self.addCleanup(channel_patcher.stop)

    def _release(self, version: str, tag: str, with_sidecar: bool) -> dict:
        assets = []
        if with_sidecar:
            assets.append({
                "name": f"VRCT_{version}_x64-setup.exe.sha256",
                "browser_download_url": f"https://example.invalid/{version}.sha256",
            })
        return {"name": version, "tag_name": tag, "assets": assets}

    def _fake_get(self, releases: list, responses: dict, requested: list):
        """GitHub のリリース一覧・.sha256・setup.exe を URL で出し分ける。
        responses に無い URL は 404 (raise_for_status が例外)。"""
        def fake_get(url, *args, **kwargs):
            requested.append(url)
            if url == config.GITHUB_RELEASES_LIST_URL:
                return _make_json_response(releases)
            if url not in responses:
                response = Mock()
                response.raise_for_status.side_effect = Exception("404")
                return response
            return responses[url]
        return fake_get

    def test_setup_download_url_follows_the_target_version(self) -> None:
        self.assertEqual(
            config.setupDownloadUrl("3.5.1-beta.1", tag="v3.5.1-beta.1"),
            "https://huggingface.co/ms-software/VRCT-beta/resolve/v3.5.1-beta.1/VRCT_setup.exe",
        )
        self.assertEqual(
            config.setupDownloadUrl("3.5.0", tag="v3.5.0"),
            "https://huggingface.co/ms-software/VRCT/resolve/v3.5.0/VRCT_setup.exe",
        )

    def test_setup_download_url_without_tag_is_main_of_the_versions_channel(self) -> None:
        self.assertEqual(config.setupDownloadUrl(), self.STABLE_MAIN)
        self.assertEqual(config.setupDownloadUrl("3.5.1-beta.1"), self.BETA_MAIN)
        self.assertEqual(config.setupDownloadUrl("3.5.1-rc.1"), self.BETA_MAIN)

    @patch("model.os_exit")
    @patch("model.psutil_Process")
    @patch("model.Popen")
    @patch("model.requests_get")
    def test_installs_older_version_from_its_own_tag(
        self, requests_get: Mock, popen: Mock, psutil_process: Mock, os_exit: Mock
    ) -> None:
        target = "3.5.1-beta.1"
        # tag_name は GitHub が返したものをそのまま使う ("v"+version と決め打ちしない)
        tag = "v3.5.1-beta.1-custom"
        tag_url = config.setupDownloadUrl(target, tag=tag)
        requested: list = []
        requests_get.side_effect = self._fake_get(
            [self._release("3.5.1-beta.2", "v3.5.1-beta.2", False), self._release(target, tag, True)],
            {
                f"https://example.invalid/{target}.sha256": _make_text_response(self.sha256),
                tag_url: _make_download_response(self.payload),
                # main (= 最新版) の setup.exe は指定版とは別物
                self.BETA_MAIN: _make_download_response(b"other" * 300_000),
            },
            requested,
        )

        self.assertEqual(Model.updateSoftware(target), SETUP_LAUNCHED)

        self.assertIn(tag_url, requested)
        self.assertNotIn(self.BETA_MAIN, requested)
        popen.assert_called_once()
        args = popen.call_args.args[0]
        self.assertIn(f"/VERSION={target}", args)
        # 現在のチャンネルは stable でも、入れる版のチャンネルを渡す
        self.assertIn("/CHANNEL=beta", args)

    @patch("model.os_exit")
    @patch("model.psutil_Process")
    @patch("model.Popen")
    @patch("model.requests_get")
    def test_legacy_release_without_tagged_setup_falls_back_to_latest_installer(
        self, requests_get: Mock, popen: Mock, psutil_process: Mock, os_exit: Mock
    ) -> None:
        # 3.4.3 には .sha256 も HF のタグ上の setup.exe も無い。インストーラは
        # /VERSION で入れる版を決めるので、main のものを (サイズ検証だけで) 使う
        target = "3.4.3"
        requested: list = []
        requests_get.side_effect = self._fake_get(
            [self._release(target, "v3.4.3", False)],
            {self.STABLE_MAIN: _make_download_response(self.payload)},
            requested,
        )

        with patch("model.errorLogging"):
            self.assertEqual(Model.updateSoftware(target), SETUP_LAUNCHED)

        self.assertIn(config.setupDownloadUrl(target, tag="v3.4.3"), requested)
        self.assertIn(self.STABLE_MAIN, requested)
        self.assertIn(f"/VERSION={target}", popen.call_args.args[0])

    @patch("model.Popen")
    @patch("model.requests_get")
    def test_verified_release_never_falls_back_to_main(
        self, requests_get: Mock, popen: Mock
    ) -> None:
        # .sha256 が公開されている版でタグ上の setup.exe が取れないとき、main
        # (別の版) を取ってくるとハッシュが合わない。検証できるものを黙って
        # 差し替えない
        target = "3.5.1-beta.1"
        requested: list = []
        requests_get.side_effect = self._fake_get(
            [self._release(target, "v3.5.1-beta.1", True)],
            {
                f"https://example.invalid/{target}.sha256": _make_text_response(self.sha256),
                self.BETA_MAIN: _make_download_response(self.payload),
            },
            requested,
        )

        with patch("model.errorLogging"):
            self.assertEqual(Model.updateSoftware(target), SETUP_DOWNLOAD_FAILED)

        self.assertNotIn(self.BETA_MAIN, requested)
        popen.assert_not_called()

    @patch("model.Popen")
    @patch("model.requests_get")
    def test_hash_mismatch_is_reported_as_verify_failure(
        self, requests_get: Mock, popen: Mock
    ) -> None:
        target = "3.5.1-beta.1"
        tag_url = config.setupDownloadUrl(target, tag="v3.5.1-beta.1")
        requests_get.side_effect = self._fake_get(
            [self._release(target, "v3.5.1-beta.1", True)],
            {
                f"https://example.invalid/{target}.sha256": _make_text_response("0" * 64),
                tag_url: _make_download_response(self.payload),
            },
            [],
        )

        with patch("model.printLog"):
            self.assertEqual(Model.updateCudaSoftware(target), SETUP_VERIFY_FAILED)

        popen.assert_not_called()

    @patch("model.Popen")
    @patch("model.requests_get")
    def test_unreadable_published_sidecar_is_reported_as_verify_failure(
        self, requests_get: Mock, popen: Mock
    ) -> None:
        target = "3.5.1-beta.1"
        requests_get.side_effect = self._fake_get(
            [self._release(target, "v3.5.1-beta.1", True)], {}, [],
        )

        with patch("model.errorLogging"), patch("model.printLog"):
            self.assertEqual(Model.updateSoftware(target), SETUP_VERIFY_FAILED)

        popen.assert_not_called()

    @patch("model.Popen")
    @patch("model.requests_get")
    def test_launches_nothing_when_download_fails(
        self, requests_get: Mock, popen: Mock
    ) -> None:
        requests_get.side_effect = Exception("network error")

        with patch("model.errorLogging"):
            self.assertEqual(Model.updateSoftware("3.5.1-beta.1"), SETUP_DOWNLOAD_FAILED)
            self.assertEqual(Model.updateCudaSoftware("3.5.1-beta.1"), SETUP_DOWNLOAD_FAILED)

        popen.assert_not_called()


class TestCheckSoftwareUpdatedBetaChannel(unittest.TestCase):
    """Beta-channel latest-version detection must stay within beta releases.

    GitHub's releases-list API is ordered by creation date, not by channel or
    semver, so a stable release published after a beta one can otherwise sort
    ahead of it and get reported to beta users as "an update is available".
    """

    def setUp(self) -> None:
        channel_patcher = patch.object(type(config), "SELECTED_RELEASE_CHANNEL", "beta")
        channel_patcher.start()
        self.addCleanup(channel_patcher.stop)

        version_patcher = patch.object(type(config), "VERSION", "3.5.1-beta.1")
        version_patcher.start()
        self.addCleanup(version_patcher.stop)

    @patch("model.errorLogging")
    @patch("model.requests_get")
    def test_ignores_newer_stable_release_listed_before_beta(
        self,
        requests_get: Mock,
        error_logging: Mock,
    ) -> None:
        # Creation-date order: stable 3.5.1 published after (and thus listed
        # before) beta 3.5.1-beta.2.
        requests_get.return_value = _make_json_response([
            {"name": "3.5.1", "prerelease": False, "draft": False},
            {"name": "3.5.1-beta.2", "prerelease": True, "draft": False},
        ])

        result = Model.checkSoftwareUpdated()

        self.assertEqual(result["new_version"], "3.5.1-beta.2")
        self.assertTrue(result["is_update_available"])
        error_logging.assert_not_called()

    @patch("model.errorLogging")
    @patch("model.requests_get")
    def test_no_update_when_only_newer_stable_exists(
        self,
        requests_get: Mock,
        error_logging: Mock,
    ) -> None:
        requests_get.return_value = _make_json_response([
            {"name": "3.5.1", "prerelease": False, "draft": False},
        ])

        result = Model.checkSoftwareUpdated()

        self.assertFalse(result["is_update_available"])
        self.assertIsNone(result["new_version"])
        error_logging.assert_not_called()


if __name__ == "__main__":
    unittest.main()
