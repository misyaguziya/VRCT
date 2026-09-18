"""VRChat chat-bubble OCR pipeline.

Captures VRChat window (via HWND or OpenVR compositor mirror), detects
chat-bubble regions with a fine-tuned YOLOv8n, OCRs them with RapidOCR
(ONNX PP-OCR), deduplicates
results, and emits recognized text via a callback so it can be fed into
the existing translation → UI/overlay pipeline.
"""

from .ocr_pipeline import OcrPipeline

__all__ = ["OcrPipeline"]
