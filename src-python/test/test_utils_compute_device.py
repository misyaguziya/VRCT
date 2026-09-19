"""CUDAデバイス列挙のテスト (2026-09-18 の torch 撤去の回帰防止)。

torch を落としたことで、デバイスの有無は ctranslate2、名前は CUDA Driver API
から取るようになった。ここで守りたいのは主に次の1点:

- CPU版ビルドでGPUを一覧に出さないこと。
  ctranslate2 は CUDA版/CPU版どちらのビルドでも GPU の存在自体は見えてしまう
  (実測: CPU版 .venv でも get_cuda_device_count() == 1)。GPU実行に必要な
  cuBLAS はCUDA版ビルドにしか同梱されないので、これを引けるかどうかで
  絞り込まないと、選ばせたあとモデル読み込みで必ず失敗する。
  torch を使っていた頃は torch.cuda.is_available() が偶然この役目を
  果たしていた。

`.venv` に pytest が入っていなくても
`python -m unittest test_utils_compute_device` で動くよう unittest で書いている。
"""

import os
import unittest
from unittest.mock import patch

import utils


def _clearGpuCaches():
    """utils 側の lru_cache を全部落とす。

    ベンダー判定 (_getGpuRuntime) もキャッシュされるので、これを消し忘れると
    先行テストが入れた偽のCDLLによる判定が次のテストへ漏れる
    (実際に test_returns_empty_when_cublas_is_not_bundled が単体では通るのに
    ファイル全体では落ちる、という形で踏んだ)。
    """
    utils._getGpuRuntime.cache_clear()
    utils._getGpuDeviceNames.cache_clear()
    utils._getAmdDeviceCapabilities.cache_clear()


class GetCudaDeviceNamesTests(unittest.TestCase):
    def setUp(self):
        _clearGpuCaches()
        self.addCleanup(_clearGpuCaches)

    def test_returns_empty_when_no_cuda_device(self):
        with patch.object(utils, "_ct2_get_cuda_device_count", return_value=0):
            self.assertEqual(utils._getGpuDeviceNames(), ())

    def test_returns_empty_when_ctranslate2_is_missing(self):
        with patch.object(utils, "_ct2_get_cuda_device_count", side_effect=RuntimeError):
            self.assertEqual(utils._getGpuDeviceNames(), ())

    def test_returns_empty_when_cublas_is_not_bundled(self):
        # CPU版ビルド。GPUはあるが ctranslate2 が使うCUDAライブラリが無い。
        with patch.object(utils, "_ct2_get_cuda_device_count", return_value=1), \
             patch.object(utils.ctypes, "CDLL", side_effect=OSError("not found")):
            self.assertEqual(utils._getGpuDeviceNames(), ())

    def test_falls_back_to_empty_name_when_driver_query_fails(self):
        # 名前が取れなくてもデバイスは出す。compute_type は "default" 側に倒れる。
        driver = unittest.mock.MagicMock()
        driver.cuInit.return_value = 0
        driver.cuDeviceGet.return_value = 1  # 失敗コード
        with patch.object(utils, "_ct2_get_cuda_device_count", return_value=2), \
             patch.object(utils.ctypes, "CDLL", return_value=driver):
            self.assertEqual(utils._getGpuDeviceNames(), ("", ""))

    def test_caches_result(self):
        with patch.object(utils, "_ct2_get_cuda_device_count", return_value=0) as counter:
            utils._getGpuDeviceNames()
            utils._getGpuDeviceNames()
            self.assertEqual(counter.call_count, 1)


class ComputeDeviceListTests(unittest.TestCase):
    def setUp(self):
        _clearGpuCaches()
        self.addCleanup(_clearGpuCaches)

    def test_lists_cpu_only_without_usable_cuda(self):
        with patch.object(utils, "_getGpuDeviceNames", return_value=()):
            devices = utils.getComputeDeviceList()
        self.assertEqual([d["device"] for d in devices], ["cpu"])

    def test_lists_each_cuda_device_with_its_name(self):
        with patch.object(utils, "_getGpuDeviceNames", return_value=("NVIDIA GeForce RTX 4090", "Tesla T4")), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float16", "float32"]):
            devices = utils.getComputeDeviceList()
        self.assertEqual(
            [(d["device"], d["device_index"], d["device_name"]) for d in devices],
            [("cpu", 0, "cpu"), ("cuda", 0, "NVIDIA GeForce RTX 4090"), ("cuda", 1, "Tesla T4")],
        )

    def test_drops_unsupported_compute_types_on_gtx(self):
        with patch.object(utils, "_getGpuDeviceNames", return_value=("NVIDIA GeForce GTX 1080",)), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float16", "int8", "float32"]):
            devices = utils.getComputeDeviceList()
        self.assertEqual(devices[1]["compute_types"], ["auto", "float32"])

    def test_restricts_unknown_gpu_to_float32(self):
        with patch.object(utils, "_getGpuDeviceNames", return_value=("NVIDIA T400",)), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float16", "float32"]):
            devices = utils.getComputeDeviceList()
        self.assertEqual(devices[1]["compute_types"], ["float32"])


class BestComputeTypeTests(unittest.TestCase):
    def setUp(self):
        _clearGpuCaches()
        self.addCleanup(_clearGpuCaches)

    def test_picks_preferred_type_for_named_gpu(self):
        with patch.object(utils, "_getGpuDeviceNames", return_value=("NVIDIA GeForce RTX 2080 Ti",)), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float32", "int8_float16"]):
            self.assertEqual(utils.getBestComputeType("cuda", 0), "int8_float16")

    def test_gtx_falls_back_to_float32(self):
        with patch.object(utils, "_getGpuDeviceNames", return_value=("NVIDIA GeForce GTX 1080",)), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float32", "int8_float16"]):
            self.assertEqual(utils.getBestComputeType("cuda", 0), "float32")

    def test_out_of_range_device_index_does_not_raise(self):
        with patch.object(utils, "_getGpuDeviceNames", return_value=()), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float32"]):
            self.assertEqual(utils.getBestComputeType("cuda", 9), "float32")

    def test_cpu_never_queries_the_driver(self):
        with patch.object(utils, "_getGpuDeviceNames", side_effect=AssertionError("must not be called")), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["int8", "float32"]):
            self.assertEqual(utils.getBestComputeType("cpu", 0), "int8")


# ---------------------------------------------------------------------------
# 以下は AMD (ROCm) 対応の追加分 (PR-4)。
#
# 実機が無いので、ベンダー判定に使う DLL のロードと HIP ドライバを偽装して
# 検証する。上の既存テスト群は1つも変更していない (パッチ対象の関数名が
# _getCudaDeviceNames -> _getGpuDeviceNames に変わっただけ)。それが
# 「CUDA版の挙動を変えていない」の機械的な保証になっている。
# ---------------------------------------------------------------------------

def _fakeCdll(loadable):
    """指定した名前だけロードできる ctypes.CDLL の代役を返す。

    loadable: {DLL名: 返すオブジェクト}。ここに無い名前は OSError。
    """
    def _cdll(name, *args, **kwargs):
        if name in loadable:
            return loadable[name]
        raise OSError(f"fake: {name} not found")
    return _cdll


def _fakeHipDriver(devices):
    """HIP ドライバの代役。devices は [(name, major, minor), ...]。

    本番コードの呼び出し方に合わせてある。`hipDeviceGet` だけ `ctypes.byref`
    (= `_obj` を持つ CArgObject) を受け取り、残りは `c_int` をそのまま受ける
    ので、値の読み方が違う。ここを取り違えると本番側の except に例外が
    飲まれ、「デバイスが一覧に出ない」という分かりにくい失敗になる。
    """
    driver = unittest.mock.MagicMock()
    driver.hipInit.return_value = 0

    def hip_device_get(device_ref, index):
        device_ref._obj.value = index
        return 0

    def hip_device_get_name(buffer, length, device):
        buffer.value = devices[device.value][0].encode("utf-8")
        return 0

    def hip_device_compute_capability(major_ref, minor_ref, device):
        major_ref._obj.value = devices[device.value][1]
        minor_ref._obj.value = devices[device.value][2]
        return 0

    driver.hipDeviceGet.side_effect = hip_device_get
    driver.hipDeviceGetName.side_effect = hip_device_get_name
    driver.hipDeviceComputeCapability.side_effect = hip_device_compute_capability
    return driver


class GpuRuntimeSelectionTests(unittest.TestCase):
    def setUp(self):
        _clearGpuCaches()
        self.addCleanup(_clearGpuCaches)

    def test_no_runtime_when_neither_blas_is_available(self):
        """CPU版ビルド。どちらのベンダーのBLASも引けない。"""
        with patch.object(utils.ctypes, "CDLL", _fakeCdll({})):
            self.assertIsNone(utils._getGpuRuntime())
            self.assertIsNone(utils.getGpuRuntimeName())

    def test_nvidia_is_detected_from_cublas(self):
        with patch.object(utils.ctypes, "CDLL", _fakeCdll({"cublas64_12.dll": object()})):
            self.assertEqual(utils._getGpuRuntime().vendor, "nvidia")
            self.assertEqual(utils.getGpuRuntimeName(), "cuda")

    def test_amd_is_detected_from_hipblas(self):
        with patch.object(utils.ctypes, "CDLL", _fakeCdll({"hipblas.dll": object()})):
            self.assertEqual(utils._getGpuRuntime().vendor, "amd")
            self.assertEqual(utils.getGpuRuntimeName(), "rocm")

    def test_amd_is_detected_from_the_older_libhipblas_name(self):
        """CTranslate2 #2016 のヘッジ。

        配布 wheel は ROCm 7.2 ビルドで hipblas.dll を期待するが、AMD の
        Windows 向け HIP SDK は 7.1.1 までで、そちらは libhipblas.dll という
        名前になる。どちらでも AMD として検出できること。
        """
        with patch.object(utils.ctypes, "CDLL", _fakeCdll({"libhipblas.dll": object()})):
            self.assertEqual(utils._getGpuRuntime().vendor, "amd")

    def test_nvidia_wins_when_both_are_present(self):
        """NVIDIA と AMD が同居している異常系でも結果が決定論的であること。"""
        loadable = {"cublas64_12.dll": object(), "hipblas.dll": object()}
        with patch.object(utils.ctypes, "CDLL", _fakeCdll(loadable)):
            self.assertEqual(utils._getGpuRuntime().vendor, "nvidia")

    def test_result_is_cached(self):
        calls = []

        def counting_cdll(name, *args, **kwargs):
            calls.append(name)
            raise OSError("nope")

        with patch.object(utils.ctypes, "CDLL", counting_cdll):
            utils._getGpuRuntime()
            utils._getGpuRuntime()
        # 2回目はキャッシュから返る (= 候補DLLを再度試さない)。
        self.assertEqual(len(calls), len(utils._GPU_RUNTIMES[0].probe_libraries)
                         + len(utils._GPU_RUNTIMES[1].probe_libraries))


class AmdComputeDeviceTests(unittest.TestCase):
    def setUp(self):
        _clearGpuCaches()
        self.addCleanup(_clearGpuCaches)

    def _patchAmd(self, devices):
        """AMD 環境を丸ごと偽装するコンテキストをまとめて返す。"""
        driver = _fakeHipDriver(devices)
        loadable = {"hipblas.dll": object(), "amdhip64_7.dll": driver}
        return patch.object(utils.ctypes, "CDLL", _fakeCdll(loadable))

    def test_lists_rdna3_device_with_float16_and_float32(self):
        with self._patchAmd([("AMD Radeon RX 7900 XTX", 11, 0)]), \
             patch.object(utils, "_ct2_get_cuda_device_count", return_value=1), \
             patch.object(utils, "_ct2_get_supported_compute_types",
                          return_value=["float16", "float32", "int8", "int8_float16"]):
            devices = utils.getComputeDeviceList()

        self.assertEqual([d["device"] for d in devices], ["cpu", "cuda"])
        self.assertEqual(devices[1]["device_name"], "AMD Radeon RX 7900 XTX")
        # int8 系は実機検証が済むまで出さない。"auto" は残す。
        self.assertEqual(devices[1]["compute_types"], ["auto", "float16", "float32"])

    def test_lists_rdna4_device(self):
        with self._patchAmd([("AMD Radeon RX 9070 XT", 12, 0)]), \
             patch.object(utils, "_ct2_get_cuda_device_count", return_value=1), \
             patch.object(utils, "_ct2_get_supported_compute_types",
                          return_value=["float16", "float32"]):
            devices = utils.getComputeDeviceList()
        self.assertEqual([d["device"] for d in devices], ["cpu", "cuda"])

    def test_hides_devices_without_bundled_tensile_kernels(self):
        """同梱カーネルが無い世代 (Ryzen APU 等) は一覧に出さない。

        選ばせても必ずモデル読み込みで失敗する。「Ryzen APU のみ」という
        構成は実際に多いので、出さない方が正しい。
        """
        for major in (9, 10):
            with self.subTest(major=major):
                _clearGpuCaches()
                with self._patchAmd([("AMD Radeon(TM) Graphics", major, 0)]), \
                     patch.object(utils, "_ct2_get_cuda_device_count", return_value=1), \
                     patch.object(utils, "_ct2_get_supported_compute_types",
                                  return_value=["float16", "float32"]):
                    devices = utils.getComputeDeviceList()
                self.assertEqual([d["device"] for d in devices], ["cpu"])

    def test_keeps_the_real_device_index_when_an_earlier_device_is_hidden(self):
        """index は HIP の実インデックスのまま。CTranslate2 に渡る値なのでずらせない。"""
        devices_spec = [
            ("AMD Radeon(TM) Graphics", 10, 0),   # APU -- 出さない
            ("AMD Radeon RX 7900 XTX", 11, 0),    # dGPU -- 出す
        ]
        with self._patchAmd(devices_spec), \
             patch.object(utils, "_ct2_get_cuda_device_count", return_value=2), \
             patch.object(utils, "_ct2_get_supported_compute_types",
                          return_value=["float16", "float32"]):
            devices = utils.getComputeDeviceList()

        self.assertEqual(
            [(d["device"], d["device_index"], d["device_name"]) for d in devices],
            [("cpu", 0, "cpu"), ("cuda", 1, "AMD Radeon RX 7900 XTX")],
        )

    def test_hides_device_when_capability_cannot_be_read(self):
        """世代が取れなければサポート外として扱う (fail-closed)。"""
        driver = _fakeHipDriver([("AMD Radeon RX 7900 XTX", 11, 0)])
        driver.hipDeviceComputeCapability.side_effect = None
        driver.hipDeviceComputeCapability.return_value = 1  # 失敗コード
        loadable = {"hipblas.dll": object(), "amdhip64_7.dll": driver}
        with patch.object(utils.ctypes, "CDLL", _fakeCdll(loadable)), \
             patch.object(utils, "_ct2_get_cuda_device_count", return_value=1), \
             patch.object(utils, "_ct2_get_supported_compute_types",
                          return_value=["float16", "float32"]):
            devices = utils.getComputeDeviceList()
        self.assertEqual([d["device"] for d in devices], ["cpu"])

    def test_best_compute_type_prefers_float16(self):
        with self._patchAmd([("AMD Radeon RX 7900 XTX", 11, 0)]), \
             patch.object(utils, "_ct2_get_cuda_device_count", return_value=1), \
             patch.object(utils, "_ct2_get_supported_compute_types",
                          return_value=["float16", "float32", "int8_float16"]):
            self.assertEqual(utils.getBestComputeType("cuda", 0), "float16")

    def test_best_compute_type_falls_back_to_float32(self):
        with self._patchAmd([("AMD Radeon RX 7900 XTX", 11, 0)]), \
             patch.object(utils, "_ct2_get_cuda_device_count", return_value=1), \
             patch.object(utils, "_ct2_get_supported_compute_types",
                          return_value=["float32", "int8"]):
            self.assertEqual(utils.getBestComputeType("cuda", 0), "float32")

    def test_amd_does_not_use_device_name_keywords(self):
        """デバイス名が揺れても compute_type の判定が変わらないこと。

        AMD のデバイス名は "AMD Radeon(TM) Graphics" のように揺れがあり、
        NVIDIA 側のような名前キーワード一致に依存すると壊れる。
        """
        for name in ("AMD Radeon RX 7900 XTX", "AMD Radeon(TM) Graphics", "", "GTX"):
            with self.subTest(name=name):
                _clearGpuCaches()
                with self._patchAmd([(name, 11, 0)]), \
                     patch.object(utils, "_ct2_get_cuda_device_count", return_value=1), \
                     patch.object(utils, "_ct2_get_supported_compute_types",
                                  return_value=["float16", "float32"]):
                    devices = utils.getComputeDeviceList()
                self.assertEqual(devices[1]["compute_types"], ["auto", "float16", "float32"])


class HipSdkPathRegistrationTests(unittest.TestCase):
    """_registerHipSdkLibraries が CPU版/CUDA版に影響しないこと。"""

    def test_does_nothing_without_hip_path(self):
        with patch.dict(utils.os.environ, {}, clear=True), \
             patch.object(utils.os, "add_dll_directory") as add_dir:
            utils._registerHipSdkLibraries()
            add_dir.assert_not_called()

    def test_does_nothing_when_the_directory_is_missing(self):
        with patch.dict(utils.os.environ, {"HIP_PATH": r"C:\nope"}, clear=True), \
             patch.object(utils.os.path, "isdir", return_value=False), \
             patch.object(utils.os, "add_dll_directory") as add_dir:
            utils._registerHipSdkLibraries()
            add_dir.assert_not_called()

    def test_registers_the_bin_directory_when_present(self):
        with patch.dict(utils.os.environ, {"HIP_PATH": r"C:\rocm"}, clear=True), \
             patch.object(utils.os.path, "isdir", return_value=True), \
             patch.object(utils.os, "add_dll_directory") as add_dir:
            utils._registerHipSdkLibraries()
            add_dir.assert_called_once_with(os.path.join(r"C:\rocm", "bin"))
            self.assertIn(os.path.join(r"C:\rocm", "bin"), utils.os.environ["PATH"])


if __name__ == "__main__":
    unittest.main()
