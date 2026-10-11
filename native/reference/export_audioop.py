"""PCM の変換 (audioop の ratecv / lin2lin / bias / tomono、PcmAudio の get_raw_data / get_wav_data、
VAD の Pcm16MonoNormalizer) を、今の Python 版で記録する。

    python native/reference/export_audioop.py   ->  native/testdata/audio/audioop.json

入力は決まった乱数で作る。ratecv は状態を引き継いで分割して呼ぶ場合も記録する。
"""

import audioop
import base64
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))

RATES = [8000, 11025, 16000, 22050, 32000, 44100, 48000, 96000]


def b64(data):
    return base64.b64encode(data).decode()


def pcm(rng, frames, width, channels=1, kind="random"):
    """random: full range; speech: a smooth wave with noise; extremes: min/max values"""
    lo, hi = -(1 << (8 * width - 1)), (1 << (8 * width - 1)) - 1
    out = bytearray()
    for i in range(frames * channels):
        if kind == "random":
            v = rng.randint(lo, hi)
        elif kind == "extremes":
            v = rng.choice([lo, hi, lo + 1, hi - 1, 0, -1, 1])
        else:
            v = int(hi * 0.6 * ((i * 37 % 200) / 100 - 1)) + rng.randint(-hi // 50, hi // 50)
            v = max(lo, min(hi, v))
        out += v.to_bytes(width, "little", signed=True)
    return bytes(out)


def main():
    from models.transcription.pcm_audio import PcmAudio
    from models.transcription.audio_vad import Pcm16MonoNormalizer
    rng = random.Random(20261012)
    cases = {"ratecv": [], "ratecv_chunked": [], "lin2lin": [], "bias": [], "tomono": [], "pcm_audio": [],
             "normalizer": []}
    for width in (1, 2, 3, 4):
        for channels in (1, 2):
            for inrate, outrate in [(48000, 16000), (44100, 16000), (16000, 48000), (22050, 44100), (8000, 11025),
                                    (96000, 16000), (16000, 16000)]:
                for kind in ("random", "speech", "extremes"):
                    data = pcm(rng, rng.choice([0, 1, 7, 300]), width, channels, kind)
                    out, state = audioop.ratecv(data, width, channels, inrate, outrate, None)
                    cases["ratecv"].append({"width": width, "channels": channels, "inrate": inrate, "outrate": outrate,
                                            "input": b64(data), "output": b64(out), "state": state})
            for weights in [(1, 0), (2, 1), (3, 7)]:
                data = pcm(rng, 200, width, channels, "speech")
                out, state = audioop.ratecv(data, width, channels, 44100, 16000, None, *weights)
                cases["ratecv"].append({"width": width, "channels": channels, "inrate": 44100, "outrate": 16000,
                                        "weights": weights, "input": b64(data), "output": b64(out), "state": state})
    for inrate in RATES:
        data = pcm(rng, inrate // 4, 2, 1, "speech")
        chunks, state, outs, pos = [], None, [], 0
        while pos < len(data):
            n = rng.choice([2, 64, 1024, 2048, 3000]) * 2
            out, state = audioop.ratecv(data[pos:pos + n], 2, 1, inrate, 16000, state)
            chunks.append(n)
            outs.append(b64(out))
            pos += n
        cases["ratecv_chunked"].append({"inrate": inrate, "input": b64(data), "chunks": chunks, "outputs": outs,
                                        "state": state})
    for width in (1, 2, 3, 4):
        for newwidth in (1, 2, 3, 4):
            data = pcm(rng, 100, width, 1, rng.choice(["random", "extremes"]))
            cases["lin2lin"].append({"width": width, "newwidth": newwidth, "input": b64(data),
                                     "output": b64(audioop.lin2lin(data, width, newwidth))})
        for bias in (-128, 128, 1, -1, 1 << 20):
            data = pcm(rng, 50, width, 1, "extremes")
            cases["bias"].append({"width": width, "bias": bias, "input": b64(data),
                                  "output": b64(audioop.bias(data, width, bias))})
        data = pcm(rng, 100, width, 2, rng.choice(["random", "extremes"]))
        cases["tomono"].append({"width": width, "input": b64(data), "output": b64(audioop.tomono(data, width, 1, 1))})
    for width in (1, 2, 3, 4):
        for rate in (8000, 16000, 44100, 48000):
            data = pcm(rng, rng.choice([0, 1, 333, 1601]), width, 1, "speech")
            if width == 1:  # PcmAudio's 8-bit PCM is unsigned
                data = audioop.bias(data, 1, 128)
            audio = PcmAudio(data, rate, width)
            for convert_rate, convert_width in [(None, None), (16000, 2), (8000, 1), (rate, 3), (48000, 4)]:
                cases["pcm_audio"].append({
                    "width": width, "rate": rate, "convert_rate": convert_rate, "convert_width": convert_width,
                    "input": b64(data), "raw": b64(audio.get_raw_data(convert_rate, convert_width)),
                    "wav": b64(audio.get_wav_data(convert_rate, convert_width))})
    for width, channels, rate in [(2, 1, 48000), (2, 2, 48000), (4, 2, 44100), (3, 6, 96000), (1, 1, 8000),
                                  (2, 1, 16000)]:
        normalizer = Pcm16MonoNormalizer(rate, width, channels)
        data = pcm(rng, rate // 5, width, channels, "speech")
        frame = width * channels
        chunks, outs, pos = [], [], 0
        while pos < len(data):
            n = rng.choice([1, 100, 480, 1024]) * frame
            outs.append(b64(normalizer.process(data[pos:pos + n])))
            chunks.append(n)
            pos += n
        cases["normalizer"].append({"width": width, "channels": channels, "rate": rate, "input": b64(data),
                                    "chunks": chunks, "outputs": outs})
    out = ROOT / "native" / "testdata" / "audio" / "audioop.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cases), encoding="utf-8")
    print(out, {k: len(v) for k, v in cases.items()}, out.stat().st_size)


if __name__ == "__main__":
    main()
