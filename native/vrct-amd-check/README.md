# VRCT AMD hardware check — 0.3.1

[日本語の説明](README.ja.md) / [はじめに（短い実行手順）](はじめに.txt)

## Volunteers

This offline Windows x64 tool checks Radeon GPU speech recognition and translation.
It does not download anything, send data, or read/change VRCT settings. Run it from
a writable folder outside your VRCT installation.

1. Extract the **complete 0.3.1 package**. Do not combine the old executable,
   adapters, or quantized Whisper models with this package.
2. Keep your normal Adrenalin driver. Do not install the HIP SDK just for this test.
3. Close games and GPU-heavy applications; double-click `run.bat`.
4. Send `vrct_amd_check_report.txt` and `.json`, GPU model, driver version, and
   whether a HIP SDK was already installed. Review the redacted reports first.

A FAIL, BLOCKED comparison, or partial report is useful. Please share it.
The default synthetic utterance is “Hello, how are you today?”. Tests are short
functional probes, not a long-session stability or multilingual quality test.

The optional llama.cpp translation test needs a separately supplied compatible
local GGUF as `models/translation.gguf`. No translation LLM is bundled. NLLB and
llama.cpp use different models and are **not** ranked against one another.

## What changed in 0.3.1

Every supervised CT2 worker starts with `AMD_COMGR_CACHE=0`, overriding any
inherited value only in that child. The worker verifies this before loading
vendor DLLs. Whisper.cpp/Vulkan, HIP inventory, the parent process and persistent
Windows environment settings are not changed.

This works around ROCm COMGR's LLVM cache-pruning crash on non-ASCII Windows
cache paths (`LLVM ERROR: Can't get available size`). It does not change models,
compute precision or decoder settings. Compilation, model load and warmup may
take longer; effects on warmed inference must still be checked on AMD hardware.

Each supervised CT2 check records `data.ct2_comgr_cache` in both JSON and text:

- `configured_value: "0"`: value supplied when constructing the child process.
- `observed_disabled`: true/false when the child reported its state; null when
  no unambiguous startup observation was captured.
- `verified_before_vendor_load`: true only after the child's flushed startup
  confirmation. Missing/malformed/duplicate confirmations cannot verify it.
- `environment_variable`, `scope` and `reason` identify the applied policy.

The record survives a child crash or timeout and never converts that failure
into a successful inference. A skipped worker has no applied-state record.
Matched comparisons require verified CT2 application and include the policy
in their benchmark contract; older cache-enabled results cannot be mixed in.
The report schema remains 3; the diagnostic version identifies this update.

## Common-mel benchmark (since 0.3.0)

The old tool timed a new whisper-cli process for every request, but timed CT2
with an already loaded model. Those durations cannot rank the two engines.
Schema 3 uses resident DLL workers with a common mel tensor and a shared minimum
audio length. It supersedes 0.2.0, whose two native frontends padded differently:

| Item | Both Whisper engines |
| --- | --- |
| Model | Verified, unquantized FP16 large-v3-turbo artifacts |
| Audio | Identical local 16 kHz mono PCM16 WAV, 0.2 to 30 seconds |
| Setup | One model load and common 128 x 3000 mel preparation per worker, outside timing |
| Warmup | One request on that same model, outside statistics |
| Measurement | Prepared features → encoder → decoder → completed UTF-8 text |
| Repetition | `--runs` requests on the same model; default 3 |
| Statistics | Every sample, warmup, best and median; engine ranking uses median |
| Decoder | Greedy, beam 1, best-of 1, temperature 0, no temperature fallback |
| Other settings | English transcription, no timestamps/history/VAD, 4 threads,
| | maximum 128 generated tokens, blank/non-speech suppression, no Flash Attention |

WAV reading, tokenizers, mel preparation, model load/destruction, process startup
and warmup are excluded. Setup and warmup times remain separate in the report.
No `total - load` estimate or fresh-process wall time is used for Whisper ranking.
`isolation.wall_seconds` is retained solely as process supervision evidence.

Both workers use `PreparedMel::from_audio`: the same Rust Slaney frontend,
normalization and feature-domain zero padding produce a row-major `[128, 3000]`
float32 tensor. CT2 receives this buffer directly. The new protocol-2 whisper
adapter uses `whisper_set_mel()` to copy exactly the same values, then
`whisper_full(context, params, nullptr, 0)` for warmup and each timed request.
It never calls the PCM-to-mel API. `duration_ms` preserves the original sample
count divided by 16 (sub-millisecond remainder discarded), while the encoder
always receives all 3000 frames. Single-segment/no-timestamp decoding uses one
window. A failed prepare invalidates the previous prepared state.

Each worker records `input_features`: frontend version, shape, row-major layout,
float32 little-endian SHA-256 over every final value, original sample count,
duration and valid frame count. The supervisor independently prepares the same
input once, outside timing. Both worker records must exactly match that expected
metadata before any ratio is produced; agreement between two wrong declarations
alone is insufficient. This compares common-mel inference, not the speed or
quality of each engine's stock audio frontend. Internal formats and kernels can
still differ; bitwise arithmetic parity is not claimed.

CT2 v4.9.0 internally limits generated tokens to
`min(options.max_length / 2, options.max_length - start_step)`. The adapter uses
256 with the fixed short prompt to obtain a 128-token generation cap. Reaching
the cap is a failure, not a successful truncated speed sample.

### Reading comparisons

- **Matched Whisper GPU comparison** uses CT2's effective FP16 GPU result and
  whisper.cpp's verified Vulkan result. The selected Vulkan device name must
  uniquely match the single HIP GPU; ambiguous or different GPUs block ranking.
- **Matched Whisper CPU comparison** uses CT2 CPU float32 and the whisper.cpp CPU
  backend with the same verified FP16 source weights. CT2 expands weights to
  float32; whisper.cpp retains its native FP16-weight CPU kernels. The report
  does not claim their internal arithmetic or memory layouts are identical.
- A normalized transcript must agree across warmup, repetitions and both engines.
  The bundled utterance is also checked against the expected words. Custom audio
  still needs manual semantic review.
- A missing/failed worker, fallback, different contract, incomplete samples,
  unverified model hashes, missing/different common-feature metadata, or different text produces **BLOCKED**, without a
  cross-engine ratio. Unknown/old quantized 128-mel models can still be diagnosed; they
  cannot produce a matched ranking. Other mel geometries are explicitly rejected.
- `vulkan_over_ct2_median` means Vulkan latency divided by CT2 latency: greater
  than one means CT2 was faster in that run. CPU/GPU speedups within an engine
  have different CPU baselines and must not be used to rank engines.
- CT2 INT8_FLOAT16, CPU INT8, NLLB, and two-thread shared-model tests remain
  additional diagnostic cases. They are not substituted into the matched pair.
- llama.cpp retains its explicitly labelled fresh-process wall-time metric.
  It is not a Whisper or NLLB comparison.

## Package layout

```text
vrct-amd-check/
  vrct-amd-check.exe
  vrct_ct2_49_adapter.dll          # protocol 2; rebuild with the 0.3.1 executable
  ctranslate2.dll                 # supplied CT2 4.9.0 ROCm DLL
  libiomp5md.dll
  run.bat
  README.ja.md                   # Japanese usage and report guide
  はじめに.txt                    # Japanese quick start
  hip/                            # dependencies + vendor kernel directory layout
  whisper-vulkan/
    whisper.dll                   # pinned lemonade-sdk v1.8.4 release
    vrct_whisper_184_adapter.dll
    ggml.dll
    ggml-base.dll
    ggml-cpu.dll
    ggml-vulkan.dll
    ... other upstream archive files ...
  llama-vulkan/                   # optional
  models/
    whisper-ct2-fp16/             # matching model.bin/config/tokenizer/etc.
    ggml-large-v3-turbo.bin       # FP16, NOT q8_0
    nllb-ct2/
    translation.gguf             # optional, user supplied
  licenses/
```

The new FP16 Whisper model pair is roughly 3.2 GB before archive compression.
The diagnostic checks model.bin, tokenizer and config SHA-256 against the pinned
pair, not a filename or an editable manifest declaration. Hashing is outside
all inference timers.

| Input | Pinned source |
| --- | --- |
| CT2 DLL | OpenNMT/CTranslate2 v4.9.0 Windows ROCm release |
| whisper DLL | lemonade-sdk/whisper.cpp-rocm v1.8.4 Windows Vulkan x64 |
| CT2 FP16 model | deepdml/faster-whisper-large-v3-turbo-ct2 @ `4df90f75321148c3a29a9e2351b7ddf8f5b115a8` |
| GGML FP16 model | ggerganov/whisper.cpp @ `98aa99a0a9db05ae2342309f5096248665f7cba3` |

Exact archive/model hashes are in `package.ps1` and `src/benchmark.rs`.
FP16 conversion artifacts share the OpenAI large-v3-turbo model family; their
serialized bytes differ. Do not claim identical conversion arithmetic.

CT2, whisper.cpp, OpenAI Whisper and the HIP components use their supplied MIT
licenses. NLLB-200 is **CC BY-NC 4.0 (non-commercial use only)**. Preserve all
license texts under `licenses/` and `hip/licenses/`. Any optional LLM remains
subject to its publisher's license and regional restrictions.

## Build (maintainer)

Use PowerShell, cached Cargo dependencies and MSVC from `native/`. No app crate,
app DLL or VRCT configuration is modified. Both adapters are optional for normal
workspace checks. Missing build inputs cause explicit SKIPs at runtime;
incorrectly supplied inputs fail the build. The Rust supervisor does not link
vendor DLLs. All DLL initialization/inference happens in deadline-supervised
children after the Windows Job Object handshake.

```powershell
cd native
$env:CARGO_NET_OFFLINE = 'true'
$env:VRCT_CT2_49_INCLUDE = 'D:\ct2-4.9.0-source\include'
$env:VRCT_CT2_49_DLL_DIR = 'D:\ct2-4.9.0-rocm'
$env:VRCT_WHISPER_184_ROOT = 'D:\whisper.cpp-rocm-1.8.4'
$env:VRCT_WHISPER_184_DLL_DIR = 'D:\whisper-v1.8.4-vulkan'
cargo build --release -p vrct-amd-check --target-dir vrct-amd-check/target-49
```

CT2 headers must be from the intact official v4.9.0 tree; build.rs checks
`python/ctranslate2/version.py`. A matching x64 ctranslate2.dll supplies exports
for the import library. The CT2 adapter crosses the vendor C++ ABI internally:
use compatible release MSVC/STL/CRT (/MD), not the app's old CT2 4.6 headers.
Its protocol changed from 1 to 2 so an old beam-5 adapter cannot silently run.

Whisper headers must be from **lemonade-sdk/whisper.cpp-rocm tag v1.8.4**. Supply
`include/whisper.h` and `ggml/include/{ggml,ggml-cpu,ggml-backend,ggml-alloc}.h` in
that layout. Build.rs verifies each header hash and derives an import library
from the matching whisper.dll. Runtime also checks the library version and requires the new prepare ABI
(protocol 2); old protocol-1 PCM adapters are rejected before invocation.
Never handwrite the whisper_full_params structure in Rust or mix release ABIs.

The build produces the exe and two adapter DLLs. Place the whisper adapter in
`whisper-vulkan/`, alongside whisper.dll; place the CT2 adapter beside the exe.
The default Rust build and adapters require the appropriate VC runtime.

`package.ps1` assembles the pinned binaries, full FP16 pair, HIP assets and
licenses into **native/target/amd-check-package-v3.1/vrct-amd-check/**. It preserves
the original v0.1, v0.2 and v0.3.0 package directories. It uses/rechecks its download cache and
never changes the app's native libraries. Build both adapters first.

```powershell
.\vrct-amd-check\package.ps1
```

For a CUDA self-test, supply a matching CT2 4.9.0 CUDA DLL/runtime instead, build
against it, and run the isolated test package with `--allow-non-rocm`. That mode
never claims AMD support; the matched GPU comparison remains blocked if no
single HIP device identity can be established. CPU matching and individual
Vulkan/CT2 workers can still be checked. Do not distribute the CUDA DLL as ROCm.

## Run and safety

```powershell
.\vrct-amd-check.exe --runs 3 --timeout 900
.\vrct-amd-check.exe --audio C:\samples\speech.wav --runs 5
```

`--help` lists local model overrides, optional NLLB tokenizer, Vulkan device index
and ROCm stage limits. Relative paths are resolved against the executable.
Custom WAV must be 16 kHz mono PCM16 and contain 3200..480000 samples
(0.2..30 seconds). Both RIFF data size and decoded length are checked. Too-short
or long input is rejected rather than silently padded or truncated. No network model paths are accepted.

Every vendor API case has its own deadline-supervised process. Failures do not
prevent other precision/CPU/Vulkan checks. A worker must return a result **and
exit normally**; a teardown hang or crash becomes FAIL. GPU enumeration/imports
alone are not inference success. CT2 ROCm uses the `device="cuda"` API name.
System32/driver versus bundled HIP origins are recorded separately. Bundling HIP
DLLs does not prove a driver-only installation works.

Reports and synthetic audio are written beside the exe. Existing different
default audio is not overwritten. Captured logs are bounded and names/home paths
are redacted before writing; review before sharing. Optional CLI scratch/config
locations are redirected under the package. Saving a diagnostic report exits 0
even if a check failed; argument/report-writing failures exit 1.

## Verification

```powershell
cargo fmt -p vrct-amd-check -- --check
cargo test -p vrct-amd-check
cargo clippy --workspace --all-targets -- -D warnings
```

Tests cover timing-contract mismatches, warmup exclusion/statistics, exact common-feature digest/shape/sample matching,
0.2/30-second length boundaries, missing or failed measurements, different physical GPUs, quality/precision mismatch,
unknown model pairs, PE parsing, redaction, gating, job isolation and timeouts.
They also exercise the CT2-only environment override in a real isolated child,
capture confirmation after a crash, and reject comparisons with unverified
COMGR cache state. No process-global environment is modified by these tests.
Run both the adapter-disabled and enabled builds. With prepared models, check
repeated resident outputs and clean teardown on the actual target GPU. AMD
performance and compatibility remain unverified until that hardware run.
