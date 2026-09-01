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


if __name__ == "__main__":
    unittest.main()
