"""_create_recorder() が config.MIC_ENABLE_VAD/SPEAKER_ENABLE_VAD に応じて
正しい Recorder クラスを選ぶことのテスト (既定 False = 従来のエネルギー
閾値方式、オプトインで VAD 方式)。VAD はこれまで2度この領域
(WASAPI/PyAudio) で挑戦して未完了/リバートに終わっているため、既定値を
誤って変えてしまわないことを明示的に守るための回帰テスト。マイク/
スピーカーは個別に切り替え可能 (2026-09-07、単一の ENABLE_VAD から分割)
なため、一方を True にしても他方の既定 False に影響しないことも検証する。
"""
import unittest
from unittest.mock import patch

from model import MicSession, SpeakerSession
from config import config


class TestMicSessionRecorderSelection(unittest.TestCase):
    def setUp(self) -> None:
        self._original_mic_enable_vad = config.MIC_ENABLE_VAD
        self._original_speaker_enable_vad = config.SPEAKER_ENABLE_VAD

    def tearDown(self) -> None:
        config.MIC_ENABLE_VAD = self._original_mic_enable_vad
        config.SPEAKER_ENABLE_VAD = self._original_speaker_enable_vad

    @patch("model.SelectedMicVadRecorder")
    @patch("model.SelectedMicEnergyAndAudioRecorder")
    def test_uses_energy_recorder_by_default(self, energy_cls, vad_cls) -> None:
        config.MIC_ENABLE_VAD = False
        session = MicSession()

        session._create_recorder({"index": 1, "defaultSampleRate": 16000})

        energy_cls.assert_called_once()
        vad_cls.assert_not_called()

    @patch("model.SelectedMicVadRecorder")
    @patch("model.SelectedMicEnergyAndAudioRecorder")
    def test_uses_vad_recorder_when_enabled(self, energy_cls, vad_cls) -> None:
        config.MIC_ENABLE_VAD = True
        session = MicSession()

        session._create_recorder({"index": 1, "defaultSampleRate": 16000})

        vad_cls.assert_called_once()
        energy_cls.assert_not_called()

    @patch("model.SelectedMicVadRecorder")
    @patch("model.SelectedMicEnergyAndAudioRecorder")
    def test_speaker_enable_vad_does_not_affect_mic(self, energy_cls, vad_cls) -> None:
        config.MIC_ENABLE_VAD = False
        config.SPEAKER_ENABLE_VAD = True
        session = MicSession()

        session._create_recorder({"index": 1, "defaultSampleRate": 16000})

        energy_cls.assert_called_once()
        vad_cls.assert_not_called()


class TestSpeakerSessionRecorderSelection(unittest.TestCase):
    def setUp(self) -> None:
        self._original_mic_enable_vad = config.MIC_ENABLE_VAD
        self._original_speaker_enable_vad = config.SPEAKER_ENABLE_VAD

    def tearDown(self) -> None:
        config.MIC_ENABLE_VAD = self._original_mic_enable_vad
        config.SPEAKER_ENABLE_VAD = self._original_speaker_enable_vad

    @patch("model.SelectedSpeakerVadRecorder")
    @patch("model.SelectedSpeakerEnergyAndAudioRecorder")
    def test_uses_energy_recorder_by_default(self, energy_cls, vad_cls) -> None:
        config.SPEAKER_ENABLE_VAD = False
        session = SpeakerSession()

        session._create_recorder({"index": 1, "defaultSampleRate": 48000, "maxInputChannels": 2})

        energy_cls.assert_called_once()
        vad_cls.assert_not_called()

    @patch("model.SelectedSpeakerVadRecorder")
    @patch("model.SelectedSpeakerEnergyAndAudioRecorder")
    def test_uses_vad_recorder_when_enabled(self, energy_cls, vad_cls) -> None:
        config.SPEAKER_ENABLE_VAD = True
        session = SpeakerSession()

        session._create_recorder({"index": 1, "defaultSampleRate": 48000, "maxInputChannels": 2})

        vad_cls.assert_called_once()
        energy_cls.assert_not_called()

    @patch("model.SelectedSpeakerVadRecorder")
    @patch("model.SelectedSpeakerEnergyAndAudioRecorder")
    def test_mic_enable_vad_does_not_affect_speaker(self, energy_cls, vad_cls) -> None:
        config.SPEAKER_ENABLE_VAD = False
        config.MIC_ENABLE_VAD = True
        session = SpeakerSession()

        session._create_recorder({"index": 1, "defaultSampleRate": 48000, "maxInputChannels": 2})

        energy_cls.assert_called_once()
        vad_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
