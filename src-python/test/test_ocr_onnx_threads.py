"""OCR の onnxruntime がコアを使い切らないようにする。"""
import unittest
from unittest.mock import MagicMock, patch

from models.ocr.ocr_languages import ocr_onnx_threads


class OcrOnnxThreadsTest(unittest.TestCase):
    def test_leaves_half_of_the_cores_up_to_four(self):
        for cores, expected in ((None, 1), (1, 1), (2, 1), (4, 2), (8, 4), (32, 4)):
            with patch("models.ocr.ocr_languages.os.cpu_count", return_value=cores):
                self.assertEqual(ocr_onnx_threads(), expected, cores)

    def test_detector_session_uses_the_limit(self):
        from models.ocr import ocr_bubble_detector as module

        ort = MagicMock()
        options = ort.SessionOptions.return_value
        detector = module.BubbleDetector.__new__(module.BubbleDetector)
        detector._session, detector._lock, detector.model_path = None, __import__("threading").Lock(), "model.onnx"
        with patch.object(module, "ort", ort), patch("models.ocr.ocr_languages.os.cpu_count", return_value=8):
            detector.loadModel()
        self.assertEqual(options.intra_op_num_threads, 4)
        self.assertEqual(options.inter_op_num_threads, 1)


if __name__ == "__main__":
    unittest.main()
