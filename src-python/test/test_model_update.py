import hashlib
import unittest
from unittest.mock import Mock, patch

from model import Model
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
