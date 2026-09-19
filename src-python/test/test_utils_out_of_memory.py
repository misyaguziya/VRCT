"""GPUメモリ不足判定のテスト (AMD GPU 対応 PR-1)。

判定は元々 `model.detectVRAMError` と `transcription_whisper.getWhisperModel`
の2箇所に同じ文字列比較が複製されていた。AMD (HIP) のマーカーを足すにあたり
片方だけ直す事故を防ぐため `utils.isOutOfMemoryMessage` へ寄せた。

ここで守りたいのは3点:

- 既存の CUDA 文字列の判定が一切変わっていないこと (CUDA版ユーザーの回帰防止)。
- CPU実行時の RAM 不足を「VRAM不足」と誤判定しないこと。
  誤判定すると、GPUを使っていないユーザーに無関係なGPU設定を触らせることになる。
- `detectVRAMError` の戻り値の契約 (tuple) が保たれていること。
  controller 側の4箇所がこの形に依存している。

HIP のマーカーは実機未確認 (ROCm ビルドの ctranslate2 が実際に返す文字列を
採取していない)。ここでは「マーカーを足せば効く」構造だけを守り、
文字列そのものの正しさは実機検証で確定させる。

`.venv` に pytest が入っていなくても
`python -m unittest test_utils_out_of_memory` で動くよう unittest で書いている。
"""

import unittest

from model import Model
from utils import isOutOfMemoryMessage


class IsOutOfMemoryMessageTests(unittest.TestCase):
    def test_detects_existing_cuda_markers(self):
        """撤去前から判定できていた2つ。ここが変わると CUDA版が回帰する。"""
        self.assertTrue(isOutOfMemoryMessage("CUDA out of memory"))
        self.assertTrue(isOutOfMemoryMessage("CUBLAS_STATUS_ALLOC_FAILED"))

    def test_detects_markers_embedded_in_a_longer_message(self):
        """実際に来るのは前後に文脈が付いた文字列。"""
        self.assertTrue(isOutOfMemoryMessage(
            "Failed to load model: CUDA out of memory. Tried to allocate 2.00 GiB"))
        self.assertTrue(isOutOfMemoryMessage(
            "cuBLAS failed with status CUBLAS_STATUS_ALLOC_FAILED"))

    def test_detects_hip_markers(self):
        """AMD (ROCm) 側。文字列は実機で確定させる前提の候補。"""
        self.assertTrue(isOutOfMemoryMessage("hipErrorOutOfMemory"))
        self.assertTrue(isOutOfMemoryMessage("HIPBLAS_STATUS_ALLOC_FAILED"))
        self.assertTrue(isOutOfMemoryMessage("rocblas_status_memory_error"))
        self.assertTrue(isOutOfMemoryMessage(
            "hipblasGemmEx failed: HIPBLAS_STATUS_ALLOC_FAILED"))

    def test_does_not_flag_cpu_side_memory_errors(self):
        """CPU の RAM 不足を VRAM 不足と誤分類しないこと。

        汎用の "out of memory" 一致まで広げていないことの回帰テスト。
        広げると CPU版ユーザーに GPU のエラー通知が出てしまう。
        """
        for message in (
            "Cannot allocate memory",
            "MemoryError",
            "out of memory",
            "Out of memory",
            "std::bad_alloc",
            "The paging file is too small for this operation to complete",
        ):
            with self.subTest(message=message):
                self.assertFalse(isOutOfMemoryMessage(message))

    def test_does_not_flag_unrelated_errors(self):
        for message in (
            "Unable to open file 'model.bin'",
            "Invalid compute type int8 for device cuda",
            "no kernel image is available for execution on the device",
        ):
            with self.subTest(message=message):
                self.assertFalse(isOutOfMemoryMessage(message))

    def test_handles_empty_and_falsy_input(self):
        self.assertFalse(isOutOfMemoryMessage(""))
        self.assertFalse(isOutOfMemoryMessage(None))

    def test_matching_is_case_sensitive(self):
        """ドライバが返す綴りそのままで一致させる。

        緩めると "cuda out of memory" のような別出自の文字列まで拾いうるので
        意図的に区別している。実機で綴りが違うと分かったらマーカーを直す。
        """
        self.assertFalse(isOutOfMemoryMessage("cuda out of memory"))
        self.assertFalse(isOutOfMemoryMessage("hiperroroutofmemory"))


class DetectVRAMErrorTests(unittest.TestCase):
    """controller の4箇所が依存する funnel。戻り値は (bool, str|None)。"""

    def setUp(self):
        # __init__ は重い依存を引くので既存テストと同じくバイパスする。
        # detectVRAMError はインスタンス状態を触らない。
        self.model = object.__new__(Model)

    def test_unwraps_the_value_error_raised_by_get_whisper_model(self):
        """文字起こしのモデルロード経路は ValueError に包んで上げてくる。"""
        error = ValueError("VRAM_OUT_OF_MEMORY", "CUDA out of memory (detail)")
        self.assertEqual(
            self.model.detectVRAMError(error),
            (True, "CUDA out of memory (detail)"),
        )

    def test_value_error_without_detail_falls_back_to_a_generic_message(self):
        error = ValueError("VRAM_OUT_OF_MEMORY")
        is_vram, message = self.model.detectVRAMError(error)
        self.assertTrue(is_vram)
        self.assertEqual(message, "VRAM out of memory")

    def test_matches_raw_runtime_error_from_the_translation_path(self):
        """翻訳側 (changeCTranslate2Model) は素の RuntimeError が上がる。

        getWhisperModel のような ValueError 包装が無いので、文字列一致の側で
        拾えないと翻訳の VRAM エラーが「その他のエラー」に落ちる。
        """
        error = RuntimeError("CUBLAS_STATUS_ALLOC_FAILED")
        self.assertEqual(
            self.model.detectVRAMError(error),
            (True, "CUBLAS_STATUS_ALLOC_FAILED"),
        )

    def test_matches_hip_runtime_error(self):
        error = RuntimeError("hipErrorOutOfMemory")
        is_vram, message = self.model.detectVRAMError(error)
        self.assertTrue(is_vram)
        self.assertEqual(message, "hipErrorOutOfMemory")

    def test_returns_false_none_for_unrelated_errors(self):
        self.assertEqual(
            self.model.detectVRAMError(RuntimeError("Unable to open file 'model.bin'")),
            (False, None),
        )

    def test_unrelated_value_error_is_not_treated_as_vram(self):
        """ValueError なら何でも VRAM 扱いにしていないこと。"""
        self.assertEqual(
            self.model.detectVRAMError(ValueError("SOME_OTHER_CODE", "detail")),
            (False, None),
        )


if __name__ == "__main__":
    unittest.main()
