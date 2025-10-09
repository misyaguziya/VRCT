from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / 'docs'

tokens = [
    'transcription_mic',
    'transcription_speaker',
    'selected_translation_compute_device',
    '/run/selected_translation_compute_device',
    '/run/transcription_mic',
    '/run/transcription_speaker',
]

for p in DOC_DIR.rglob('*.md'):
    text = p.read_text(encoding='utf-8')
    for i, line in enumerate(text.splitlines(), start=1):
        for t in tokens:
            if t in line:
                print(f"{p}:{i}:{line.strip()}")

print('done')
