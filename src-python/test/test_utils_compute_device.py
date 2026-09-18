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

import unittest
from unittest.mock import patch

import utils


class GetCudaDeviceNamesTests(unittest.TestCase):
    def setUp(self):
        utils._getCudaDeviceNames.cache_clear()
        self.addCleanup(utils._getCudaDeviceNames.cache_clear)

    def test_returns_empty_when_no_cuda_device(self):
        with patch.object(utils, "_ct2_get_cuda_device_count", return_value=0):
            self.assertEqual(utils._getCudaDeviceNames(), ())

    def test_returns_empty_when_ctranslate2_is_missing(self):
        with patch.object(utils, "_ct2_get_cuda_device_count", side_effect=RuntimeError):
            self.assertEqual(utils._getCudaDeviceNames(), ())

    def test_returns_empty_when_cublas_is_not_bundled(self):
        # CPU版ビルド。GPUはあるが ctranslate2 が使うCUDAライブラリが無い。
        with patch.object(utils, "_ct2_get_cuda_device_count", return_value=1), \
             patch.object(utils.ctypes, "CDLL", side_effect=OSError("not found")):
            self.assertEqual(utils._getCudaDeviceNames(), ())

    def test_falls_back_to_empty_name_when_driver_query_fails(self):
        # 名前が取れなくてもデバイスは出す。compute_type は "default" 側に倒れる。
        driver = unittest.mock.MagicMock()
        driver.cuInit.return_value = 0
        driver.cuDeviceGet.return_value = 1  # 失敗コード
        with patch.object(utils, "_ct2_get_cuda_device_count", return_value=2), \
             patch.object(utils.ctypes, "CDLL", return_value=driver):
            self.assertEqual(utils._getCudaDeviceNames(), ("", ""))

    def test_caches_result(self):
        with patch.object(utils, "_ct2_get_cuda_device_count", return_value=0) as counter:
            utils._getCudaDeviceNames()
            utils._getCudaDeviceNames()
            self.assertEqual(counter.call_count, 1)


class ComputeDeviceListTests(unittest.TestCase):
    def setUp(self):
        utils._getCudaDeviceNames.cache_clear()
        self.addCleanup(utils._getCudaDeviceNames.cache_clear)

    def test_lists_cpu_only_without_usable_cuda(self):
        with patch.object(utils, "_getCudaDeviceNames", return_value=()):
            devices = utils.getComputeDeviceList()
        self.assertEqual([d["device"] for d in devices], ["cpu"])

    def test_lists_each_cuda_device_with_its_name(self):
        with patch.object(utils, "_getCudaDeviceNames", return_value=("NVIDIA GeForce RTX 4090", "Tesla T4")), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float16", "float32"]):
            devices = utils.getComputeDeviceList()
        self.assertEqual(
            [(d["device"], d["device_index"], d["device_name"]) for d in devices],
            [("cpu", 0, "cpu"), ("cuda", 0, "NVIDIA GeForce RTX 4090"), ("cuda", 1, "Tesla T4")],
        )

    def test_drops_unsupported_compute_types_on_gtx(self):
        with patch.object(utils, "_getCudaDeviceNames", return_value=("NVIDIA GeForce GTX 1080",)), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float16", "int8", "float32"]):
            devices = utils.getComputeDeviceList()
        self.assertEqual(devices[1]["compute_types"], ["auto", "float32"])

    def test_restricts_unknown_gpu_to_float32(self):
        with patch.object(utils, "_getCudaDeviceNames", return_value=("NVIDIA T400",)), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float16", "float32"]):
            devices = utils.getComputeDeviceList()
        self.assertEqual(devices[1]["compute_types"], ["float32"])


class BestComputeTypeTests(unittest.TestCase):
    def setUp(self):
        utils._getCudaDeviceNames.cache_clear()
        self.addCleanup(utils._getCudaDeviceNames.cache_clear)

    def test_picks_preferred_type_for_named_gpu(self):
        with patch.object(utils, "_getCudaDeviceNames", return_value=("NVIDIA GeForce RTX 2080 Ti",)), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float32", "int8_float16"]):
            self.assertEqual(utils.getBestComputeType("cuda", 0), "int8_float16")

    def test_gtx_falls_back_to_float32(self):
        with patch.object(utils, "_getCudaDeviceNames", return_value=("NVIDIA GeForce GTX 1080",)), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float32", "int8_float16"]):
            self.assertEqual(utils.getBestComputeType("cuda", 0), "float32")

    def test_out_of_range_device_index_does_not_raise(self):
        with patch.object(utils, "_getCudaDeviceNames", return_value=()), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["float32"]):
            self.assertEqual(utils.getBestComputeType("cuda", 9), "float32")

    def test_cpu_never_queries_the_driver(self):
        with patch.object(utils, "_getCudaDeviceNames", side_effect=AssertionError("must not be called")), \
             patch.object(utils, "_ct2_get_supported_compute_types", return_value=["int8", "float32"]):
            self.assertEqual(utils.getBestComputeType("cpu", 0), "int8")


if __name__ == "__main__":
    unittest.main()
