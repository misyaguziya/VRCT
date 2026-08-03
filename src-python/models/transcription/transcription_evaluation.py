import re
import time
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable, Sequence


def normalize_text(text: str, remove_whitespace: bool = False) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold().strip()
    if remove_whitespace:
        return re.sub(r"\s+", "", normalized)
    return " ".join(normalized.split())


def edit_distance(reference: Sequence[Any], hypothesis: Sequence[Any]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for reference_index, reference_item in enumerate(reference, start=1):
        current = [reference_index]
        for hypothesis_index, hypothesis_item in enumerate(hypothesis, start=1):
            current.append(min(
                current[-1] + 1,
                previous[hypothesis_index] + 1,
                previous[hypothesis_index - 1] + (reference_item != hypothesis_item),
            ))
        previous = current
    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float:
    reference_chars = normalize_text(reference, remove_whitespace=True)
    hypothesis_chars = normalize_text(hypothesis, remove_whitespace=True)
    return edit_distance(reference_chars, hypothesis_chars) / max(1, len(reference_chars))


def word_error_rate(reference: str, hypothesis: str) -> float:
    reference_words = normalize_text(reference).split()
    hypothesis_words = normalize_text(hypothesis).split()
    return edit_distance(reference_words, hypothesis_words) / max(1, len(reference_words))


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    reference: str
    hypothesis: str
    cer: float
    wer: float
    processing_ms: float
    end_to_result_ms: float
    audio_duration_ms: float
    real_time_factor: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_case(
    case_id: str,
    reference: str,
    audio_duration_ms: float,
    recognize: Callable[[], str | dict[str, Any]],
) -> EvaluationResult:
    started_at = time.perf_counter()
    recognized = recognize()
    processing_ms = (time.perf_counter() - started_at) * 1000
    if isinstance(recognized, dict):
        hypothesis = str(recognized.get("text", ""))
        end_to_result_ms = recognized.get("end_to_result_ms")
        if end_to_result_ms is None:
            end_to_result_ms = processing_ms
    else:
        hypothesis = str(recognized)
        end_to_result_ms = processing_ms

    return EvaluationResult(
        case_id=case_id,
        reference=reference,
        hypothesis=hypothesis,
        cer=character_error_rate(reference, hypothesis),
        wer=word_error_rate(reference, hypothesis),
        processing_ms=processing_ms,
        end_to_result_ms=float(end_to_result_ms),
        audio_duration_ms=audio_duration_ms,
        real_time_factor=processing_ms / max(1.0, audio_duration_ms),
    )


def summarize(results: Iterable[EvaluationResult]) -> dict[str, float | int]:
    items = list(results)
    if not items:
        return {"cases": 0, "mean_cer": 0.0, "mean_wer": 0.0, "mean_processing_ms": 0.0, "mean_end_to_result_ms": 0.0, "mean_real_time_factor": 0.0}
    count = len(items)
    return {
        "cases": count,
        "mean_cer": sum(item.cer for item in items) / count,
        "mean_wer": sum(item.wer for item in items) / count,
        "mean_processing_ms": sum(item.processing_ms for item in items) / count,
        "mean_end_to_result_ms": sum(item.end_to_result_ms for item in items) / count,
        "mean_real_time_factor": sum(item.real_time_factor for item in items) / count,
    }