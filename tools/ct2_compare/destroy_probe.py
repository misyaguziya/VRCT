"""Compare CTranslate2 model destruction in isolated environments."""

from __future__ import annotations

import argparse
import gc
import sys
import time

import ctranslate2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_path")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="float32")
    parser.add_argument("--skip-inference", action="store_true")
    args = parser.parse_args()

    print(f"version={ctranslate2.__version__}", flush=True)
    print(f"module={ctranslate2.__file__}", flush=True)
    print(f"device={args.device}", flush=True)
    print("loading", flush=True)
    translator = ctranslate2.Translator(
        args.model_path,
        device=args.device,
        compute_type=args.compute_type,
        inter_threads=1,
        intra_threads=2,
    )
    print("loaded", flush=True)

    if not args.skip_inference:
        print("inference", flush=True)
        translator.translate_batch([["hello"]])
        print("inference_done", flush=True)

    print("unload_begin", flush=True)
    unload_started = time.monotonic()
    unload_model = getattr(translator, "unload_model", None)
    if unload_model is not None:
        unload_model(False)
        print(f"unload_done={time.monotonic() - unload_started:.3f}", flush=True)
    else:
        print("unload_unavailable", flush=True)

    print("delete_begin", flush=True)
    delete_started = time.monotonic()
    del translator
    print(f"delete_ref_done={time.monotonic() - delete_started:.3f}", flush=True)
    gc_started = time.monotonic()
    gc.collect()
    print(f"gc_done={time.monotonic() - gc_started:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    started = time.monotonic()
    result = main()
    print(f"finished={time.monotonic() - started:.3f}", flush=True)
    raise SystemExit(result)