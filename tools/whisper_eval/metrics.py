"""Text normalization and character error rate helpers."""

from __future__ import annotations

import unicodedata


def normalize_transcript(text: str) -> str:
    """Normalize text conservatively for Japanese CER evaluation."""

    normalized = unicodedata.normalize("NFKC", text or "")
    return "".join(character for character in normalized if not character.isspace())


def character_error_rate(reference: str, hypothesis: str) -> float:
    """Return Levenshtein distance divided by reference character count."""

    reference = normalize_transcript(reference)
    hypothesis = normalize_transcript(hypothesis)
    if not reference:
        return 0.0 if not hypothesis else 1.0

    previous = list(range(len(hypothesis) + 1))
    for reference_index, reference_character in enumerate(reference, start=1):
        current = [reference_index]
        for hypothesis_index, hypothesis_character in enumerate(hypothesis, start=1):
            substitution = previous[hypothesis_index - 1] + (
                reference_character != hypothesis_character
            )
            insertion = current[hypothesis_index - 1] + 1
            deletion = previous[hypothesis_index] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1] / len(reference)
