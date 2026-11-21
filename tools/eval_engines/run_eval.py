"""P5 の評価: 今のローカルのエンジンと、足す候補 (speech.cpp・llama.cpp) を同じ入力で比べる。

    python tools/eval_engines/run_eval.py --root D:/path/to/vrct-eval --vrct-weights <VRCT の weights の親>
        [--only asr|mt] [--engines a,b] [--devices gpu,cpu] [--limit N] [--dll-dir DIR ...]

先に fetch.py で <root> を作り、`cargo build --release -p vrct-backend --example eval_local` を済ませる。
結果は <root>/results/<engine>-<device>.json (出力そのもの) と <root>/results/summary.md (集計)。
標準ライブラリだけで動く。
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import statistics
import subprocess
import sys
import time
import unicodedata
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
NATIVE = REPO / "native"
EVAL_LOCAL = NATIVE / "target/release/examples/eval_local.exe"
LANGS = ["ja", "en", "ko", "zh"]
# 誤認識を見るための、何も話していない音声 (空が正解)
QUIET = ["silence", "noise", "tone"]
MT_DIRECTIONS = [("ja", "en"), ("en", "ja"), ("ko", "ja"), ("zh", "ja"), ("ja", "ko"), ("ja", "zh")]
NLLB_CODES = {"ja": "jpn_Jpan", "en": "eng_Latn", "ko": "kor_Hang", "zh": "zho_Hans"}
HY_NAMES = {"ja": ("Japanese", "日语"), "en": ("English", "英语"), "ko": ("Korean", "韩语"), "zh": ("Chinese", "中文")}

# name: (kind, model file or None, languages)
ASR_ENGINES = {
    "whisper-turbo": ("ct2", "weights/whisper/large-v3-turbo-int8", LANGS),
    "qwen3-asr-0.6b": ("speech", "models/Qwen3-ASR-0.6B-Q8_0.gguf", LANGS),
    "qwen3-asr-1.7b": ("speech", "models/Qwen3-ASR-1.7B-Q8_0.gguf", LANGS),
    "parakeet-ja": ("speech", "models/parakeet-tdt_ctc-0.6B-ja-Q8_0.gguf", ["ja"]),
    "reazonspeech-v2": ("speech", "models/reazonspeech-nemo-619M-v2-Q8_0.gguf", ["ja"]),
}
MT_ENGINES = {
    "nllb-600m": ("ct2", "nllb-200-distilled-600M-ct2-int8"),
    "hy-mt1.5-1.8b": ("llama", "models/HY-MT1.5-1.8B-Q4_K_M.gguf"),
}


# -- inputs -------------------------------------------------------------

def load_inputs(root, limit):
    fleurs = json.loads((root / "data/fleurs/refs.json").read_text(encoding="utf-8"))
    ids = fleurs["ids"][:limit] if limit else fleurs["ids"]
    asr = [{"id": f"{lang}-{i}", "wav": str(root / "data/fleurs" / lang / f"{i}.wav"), "language": lang,
            "ref": fleurs["text"][lang][i]} for lang in LANGS for i in ids]
    asr += [{"id": f"quiet-{name}", "wav": str(NATIVE / "testdata/whisper/audio" / f"{name}.wav"), "language": "ja",
             "ref": ""} for name in QUIET]
    mt = [{"id": f"{s}>{t}-{i}", "text": fleurs["text"][s][i], "source": s, "target": t, "ref": fleurs["text"][t][i]}
          for s, t in MT_DIRECTIONS for i in ids]
    return asr, mt


# -- metrics ------------------------------------------------------------

def normalize(text):
    text = unicodedata.normalize("NFKC", text).lower()
    return "".join(" " if unicodedata.category(c)[0] == "Z" else c for c in text
                   if unicodedata.category(c)[0] not in "PS")


def edits(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (x != y))
    return row[-1]


def error_rate(pairs, words):
    """WER (words) or CER (characters, spaces removed) over all pairs"""
    errors = total = 0
    for hyp, ref in pairs:
        h, r = normalize(hyp), normalize(ref)
        h, r = (h.split(), r.split()) if words else (h.replace(" ", ""), r.replace(" ", ""))
        errors += edits(h, r)
        total += len(r)
    return errors / max(total, 1)


def chrf(pairs, n=6, beta=2.0):
    """corpus chrF (character n-grams 1..6, spaces removed, beta 2), as sacrebleu's default"""
    def grams(s, k):
        s = s.replace(" ", "")
        out = {}
        for i in range(len(s) - k + 1):
            out[s[i:i + k]] = out.get(s[i:i + k], 0) + 1
        return out
    precision, recall = [], []
    for k in range(1, n + 1):
        match = hyp_total = ref_total = 0
        for hyp, ref in pairs:
            h, r = grams(hyp, k), grams(ref, k)
            match += sum(min(c, r.get(g, 0)) for g, c in h.items())
            hyp_total += sum(h.values())
            ref_total += sum(r.values())
        precision.append(match / hyp_total if hyp_total else 0)
        recall.append(match / ref_total if ref_total else 0)
    p, r = sum(precision) / n, sum(recall) / n
    return 0.0 if p + r == 0 else 100 * (1 + beta ** 2) * p * r / (beta ** 2 * p + r)


# -- engines ------------------------------------------------------------

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_ready(url, process, seconds=600):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if process.poll() is not None:
            sys.exit(f"server exited ({process.returncode}): {process.args}")
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.5)
    sys.exit(f"server not ready: {url}")


class Server:
    """A local server process started for one engine and stopped afterwards"""

    def __init__(self, args, health, log):
        self.port = free_port()
        args = [a.replace("{port}", str(self.port)) for a in args]
        self.log = open(log, "w", encoding="utf-8")
        started = time.perf_counter()
        self.process = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT)
        wait_ready(f"http://127.0.0.1:{self.port}{health}", self.process)
        self.load_ms = (time.perf_counter() - started) * 1000

    def stop(self):
        self.process.terminate()
        try:
            self.process.wait(30)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.log.close()


def post(url, body, content_type, timeout=600):
    request = urllib.request.Request(url, data=body, headers={"Content-Type": content_type})
    with urllib.request.urlopen(request, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def multipart(fields, file_field, file_path):
    boundary = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="a.wav"\r\n'
                 f"Content-Type: audio/wav\r\n\r\n".encode() + Path(file_path).read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def timed(items, one):
    """warm up with the first item once, then [{id, text, ms, error?}]"""
    if items:
        try:
            one(items[0])
        except Exception:
            pass
    out = []
    for item in items:
        started = time.perf_counter()
        try:
            text, error = one(item), None
        except Exception as e:
            text, error = "", f"{type(e).__name__}: {e}"
        row = {"id": item["id"], "text": text, "ms": (time.perf_counter() - started) * 1000}
        if error:
            row["error"] = error
        out.append(row)
    return out


def run_eval_local(args, items, env):
    # the mel features look for OpenBLAS next to the exe (as in the installed folder), not on PATH
    for dll in (NATIVE / "target/release").glob("*.dll"):
        if not (EVAL_LOCAL.parent / dll.name).exists():
            shutil.copy2(dll, EVAL_LOCAL.parent)
    work = Path(args[-1]).with_suffix(".in.json")
    work.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    out = Path(args[-1])
    subprocess.run([str(EVAL_LOCAL), *args[:-1], str(work), str(out)], check=True, env=env)
    return json.loads(out.read_text(encoding="utf-8"))


def asr_ct2(root, model, device, items, env, out):
    device = "cuda" if device == "gpu" else "cpu"
    data = run_eval_local(["asr", str(root / model), device, str(out)],
                          [{"id": i["id"], "wav": i["wav"], "language": i["language"]} for i in items], env)
    return data["load_ms"], data["items"]


def asr_speech(root, model, device, items, env, out):
    server = Server([str(root / "bin/speech/speech.exe"), "serve", str(root / model), "--port", "{port}",
                     "--device", device], "/health", out.with_suffix(".log"))
    url = f"http://127.0.0.1:{server.port}/v1/audio/transcriptions"
    try:
        # only Qwen3-ASR takes a language (the Japanese-only models refuse the option)
        takes_language = "Qwen3-ASR" in model

        def one(item):
            fields = {"language": item["language"]} if takes_language else {}
            body, ctype = multipart(fields, "file", item["wav"])
            return post(url, body, ctype).get("text", "")
        return server.load_ms, timed(items, one)
    finally:
        server.stop()


def mt_ct2(root, weights, model, device, items, env, out):
    device = "cuda" if device == "gpu" else "cpu"
    data = run_eval_local(["mt", str(weights), model, device, str(out)],
                          [{"id": i["id"], "text": i["text"], "source": NLLB_CODES[i["source"]],
                            "target": NLLB_CODES[i["target"]]} for i in items], env)
    return data["load_ms"], data["items"]


def hy_prompt(item):
    english, chinese = HY_NAMES[item["target"]]
    if "zh" in (item["source"], item["target"]):
        return f"将以下文本翻译为{chinese}，注意只需要输出翻译后的结果，不要额外解释：\n\n{item['text']}"
    return f"Translate the following segment into {english}, without additional explanation.\n\n{item['text']}"


def mt_llama(root, model, device, items, env, out):
    layers = ["-ngl", "999"] if device == "gpu" else ["-ngl", "0", "--device", "none"]
    server = Server([str(root / "bin/llama/llama-server.exe"), "-m", str(root / model), "--port", "{port}",
                     "-c", "4096", *layers], "/health", out.with_suffix(".log"))
    url = f"http://127.0.0.1:{server.port}/v1/chat/completions"
    try:
        def one(item):
            body = {"messages": [{"role": "user", "content": hy_prompt(item)}], "max_tokens": 512, "seed": 0,
                    # the model card's settings
                    "temperature": 0.7, "top_k": 20, "top_p": 0.6, "repeat_penalty": 1.05}
            r = post(url, json.dumps(body).encode(), "application/json")
            return r["choices"][0]["message"]["content"].strip()
        return server.load_ms, timed(items, one)
    finally:
        server.stop()


# -- summary ------------------------------------------------------------

def latency(rows):
    ms = sorted(r["ms"] for r in rows)
    if not ms:
        return "-"
    p90 = ms[min(len(ms) - 1, int(len(ms) * 0.9))]
    return f"{statistics.median(ms):.0f} / {p90:.0f}"


def summarize(root, asr_items, mt_items):
    refs = {i["id"]: i for i in asr_items + mt_items}
    lines = ["# P5 評価の集計", "", "遅延は 1 件の中央値 / 90 パーセンタイル (ms)。誤り率は日中韓が CER、英語が WER。", ""]
    asr_rows, mt_rows = [], []
    for path in sorted((root / "results").glob("*.json")):
        if path.name.endswith(".in.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data["items"]
        errors = sum(1 for r in rows if r.get("error"))
        if data["task"] == "asr":
            cells = []
            for lang in LANGS:
                rs = [r for r in rows if r["id"].startswith(lang + "-")]
                cells.append(f"{error_rate([(r['text'], refs[r['id']]['ref']) for r in rs], lang == 'en'):.1%} "
                             f"({latency(rs)})" if rs else "-")
            quiet = [r for r in rows if r["id"].startswith("quiet-")]
            heard = ", ".join(f"{r['id'][6:]}: {r['text'].strip()[:20]}" for r in quiet if r["text"].strip()) or "なし"
            asr_rows.append(f"| {data['engine']} | {data['device']} | {data['load_ms'] / 1000:.1f} s | "
                            + " | ".join(cells) + f" | {heard} | {errors} |")
        else:
            cells = []
            for s, t in MT_DIRECTIONS:
                rs = [r for r in rows if r["id"].startswith(f"{s}>{t}-")]
                cells.append(f"{chrf([(r['text'], refs[r['id']]['ref']) for r in rs]):.1f} ({latency(rs)})" if rs else "-")
            mt_rows.append(f"| {data['engine']} | {data['device']} | {data['load_ms'] / 1000:.1f} s | "
                           + " | ".join(cells) + f" | {errors} |")
    if asr_rows:
        lines += ["## 文字起こし (FLEURS test、各言語の件数は refs.json)", "",
                  "| エンジン | デバイス | 読み込み | ja | en | ko | zh | 無音で出た文字 | 失敗 |",
                  "|---|---|---|---|---|---|---|---|---|", *asr_rows, ""]
    if mt_rows:
        head = " | ".join(f"{s}→{t}" for s, t in MT_DIRECTIONS)
        lines += ["## 翻訳 (FLEURS の同じ文を正解に chrF)", "", f"| エンジン | デバイス | 読み込み | {head} | 失敗 |",
                  "|---|---|---|" + "---|" * len(MT_DIRECTIONS) + "---|", *mt_rows, ""]
    (root / "results/summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--vrct-weights", type=Path, help="the folder holding weights/ctranslate2/<NLLB> (an installed VRCT's)")
    parser.add_argument("--only", choices=["asr", "mt"])
    parser.add_argument("--engines", help="comma-separated engine names (default: all)")
    parser.add_argument("--devices", default="gpu,cpu")
    parser.add_argument("--limit", type=int, help="sentences per language (default: all in refs.json)")
    parser.add_argument("--dll-dir", action="append", default=[], help="added to PATH for eval_local (CUDA's DLLs)")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    (root / "results").mkdir(exist_ok=True)
    asr_items, mt_items = load_inputs(root, args.limit)
    if not args.summary_only:
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join([str(NATIVE / "target/release"), *map(str, args.dll_dir), env["PATH"]])
        wanted = set(args.engines.split(",")) if args.engines else None
        jobs = []
        if args.only != "mt":
            jobs += [("asr", n, e) for n, e in ASR_ENGINES.items()]
        if args.only != "asr":
            jobs += [("mt", n, e) for n, e in MT_ENGINES.items()]
        for task, name, engine in jobs:
            if wanted and name not in wanted:
                continue
            for device in args.devices.split(","):
                out = root / "results" / f"{name}-{device}.json"
                print(f"{task} {name} {device} ...", flush=True)
                if task == "asr":
                    kind, model, langs = engine
                    items = [i for i in asr_items if i["language"] in langs]
                    run = asr_ct2 if kind == "ct2" else asr_speech
                    load_ms, rows = run(root, model, device, items, env, out)
                else:
                    kind, model = engine
                    if kind == "ct2":
                        if not args.vrct_weights:
                            sys.exit("--vrct-weights is needed for nllb")
                        load_ms, rows = mt_ct2(root, args.vrct_weights, model, device, mt_items, env, out)
                    else:
                        load_ms, rows = mt_llama(root, model, device, mt_items, env, out)
                out.write_text(json.dumps({"task": task, "engine": name, "device": device, "load_ms": load_ms,
                                           "items": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    summarize(root, asr_items, mt_items)


if __name__ == "__main__":
    main()
