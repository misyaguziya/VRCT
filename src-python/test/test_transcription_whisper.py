import unittest
from unittest.mock import MagicMock, patch

from models.transcription import transcription_whisper


class TestDownloadWhisperWeight(unittest.TestCase):
    """Different upstream repos (Systran/faster-whisper-* vs Zoont/deepdml
    faster-whisper-large-v3-turbo conversions) ship different file sets.
    downloadWhisperWeight used to request a fixed candidate list regardless
    of what a given repo actually contains, producing 404s for files the
    repo never had (e.g. Systran repos have no preprocessor_config.json/
    vocabulary.json; Zoont/deepdml repos have no vocabulary.txt)."""

    def setUp(self) -> None:
        # downloadWhisperWeight always calls os_makedirs on the target path
        # before checking what to download; without this patch a real
        # directory (e.g. D:\tmp\root\weights\...) gets created on disk.
        self._makedirs_patch = patch.object(transcription_whisper, "os_makedirs")
        self._makedirs_patch.start()

    def tearDown(self) -> None:
        self._makedirs_patch.stop()

    @patch.object(transcription_whisper, "checkWhisperWeight", return_value=False)
    @patch.object(transcription_whisper, "downloadFile")
    @patch("huggingface_hub.list_repo_files")
    @patch("huggingface_hub.hf_hub_url", side_effect=lambda repo, filename: f"https://hf.example/{repo}/{filename}")
    def test_skips_files_absent_from_the_repo(
        self, mock_hub_url, mock_list_repo_files, mock_download_file, mock_check_weight
    ) -> None:
        # Systran-style repo: no preprocessor_config.json / vocabulary.json.
        mock_list_repo_files.return_value = [
            ".gitattributes", "README.md", "config.json", "model.bin",
            "tokenizer.json", "vocabulary.txt",
        ]

        transcription_whisper.downloadWhisperWeight("/tmp/root", "base")

        downloaded_filenames = {call.args[0].split("/")[-1] for call in mock_download_file.call_args_list}
        self.assertEqual(
            downloaded_filenames,
            {"config.json", "model.bin", "tokenizer.json", "vocabulary.txt"},
        )
        self.assertNotIn("preprocessor_config.json", downloaded_filenames)
        self.assertNotIn("vocabulary.json", downloaded_filenames)

    @patch.object(transcription_whisper, "checkWhisperWeight", return_value=False)
    @patch.object(transcription_whisper, "downloadFile")
    @patch("huggingface_hub.list_repo_files")
    @patch("huggingface_hub.hf_hub_url", side_effect=lambda repo, filename: f"https://hf.example/{repo}/{filename}")
    def test_downloads_preprocessor_and_vocabulary_json_when_present(
        self, mock_hub_url, mock_list_repo_files, mock_download_file, mock_check_weight
    ) -> None:
        # Zoont/deepdml-style repo: has preprocessor_config.json/vocabulary.json,
        # no vocabulary.txt.
        mock_list_repo_files.return_value = [
            ".gitattributes", "README.md", "config.json", "model.bin",
            "preprocessor_config.json", "tokenizer.json", "vocabulary.json",
        ]

        transcription_whisper.downloadWhisperWeight("/tmp/root", "large-v3-turbo")

        downloaded_filenames = {call.args[0].split("/")[-1] for call in mock_download_file.call_args_list}
        self.assertEqual(
            downloaded_filenames,
            {"config.json", "model.bin", "preprocessor_config.json", "tokenizer.json", "vocabulary.json"},
        )
        self.assertNotIn("vocabulary.txt", downloaded_filenames)

    @patch.object(transcription_whisper, "checkWhisperWeight", return_value=False)
    @patch.object(transcription_whisper, "downloadFile")
    @patch("huggingface_hub.list_repo_files", side_effect=Exception("network error"))
    @patch("huggingface_hub.hf_hub_url", side_effect=lambda repo, filename: f"https://hf.example/{repo}/{filename}")
    @patch.object(transcription_whisper, "errorLogging")
    def test_falls_back_to_full_candidate_list_when_listing_fails(
        self, mock_error_logging, mock_hub_url, mock_list_repo_files, mock_download_file, mock_check_weight
    ) -> None:
        transcription_whisper.downloadWhisperWeight("/tmp/root", "base")

        downloaded_filenames = {call.args[0].split("/")[-1] for call in mock_download_file.call_args_list}
        self.assertEqual(downloaded_filenames, set(transcription_whisper._FILENAMES))
        mock_error_logging.assert_called_once()

    @patch.object(transcription_whisper, "checkWhisperWeight", return_value=True)
    @patch.object(transcription_whisper, "downloadFile")
    @patch("huggingface_hub.list_repo_files")
    def test_skips_download_entirely_when_weight_already_verified(
        self, mock_list_repo_files, mock_download_file, mock_check_weight
    ) -> None:
        transcription_whisper.downloadWhisperWeight("/tmp/root", "base")

        mock_download_file.assert_not_called()
        mock_list_repo_files.assert_not_called()

    @patch.object(transcription_whisper, "checkWhisperWeight", return_value=False)
    @patch.object(transcription_whisper, "downloadFile")
    @patch("huggingface_hub.list_repo_files")
    @patch("huggingface_hub.hf_hub_url", side_effect=lambda repo, filename: f"https://hf.example/{repo}/{filename}")
    def test_calls_end_callback_after_download(
        self, mock_hub_url, mock_list_repo_files, mock_download_file, mock_check_weight
    ) -> None:
        mock_list_repo_files.return_value = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
        end_callback = MagicMock()

        transcription_whisper.downloadWhisperWeight("/tmp/root", "base", end_callback=end_callback)

        end_callback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
