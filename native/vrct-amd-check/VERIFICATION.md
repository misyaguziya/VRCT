# Current checkpoint — CT2 implementation handoff (2026-11-19)

The user accepted the AMD validation and authorized proceeding to app integration.
The implementation policy is CT2 for CPU, NVIDIA/CUDA and AMD/ROCm. Additional
Vulkan comparisons and whisper.cpp fixes are not prerequisites for that work.
The product sidecar itself has not yet been migrated from CT2 4.6 to 4.9.

- RX 7800 XT / gfx1101 and RX 9070 XT / gfx1201: diagnostic 0.3.1, ROCm CT2 4.9.0,
  all 11 cases and 48 requests including warmups per configuration succeeded.
- RTX 2080 Ti / NVIDIA driver 617.42: CUDA CT2 4.9.0 with a matching rebuilt
  diagnostic adapter, all 11 cases and 48 requests including warmups succeeded.
- All three configurations produced matching expected outputs within each model;
  inference children exited normally, without timeout. GPU effective compute
  types were float16/int8_float16; CPU int8 resolved to int8_float32.
- Shared-model two-thread probes passed. These do not cover simultaneous
  Whisper plus NLLB residency, repeated in-process unload/reload, VRAM release,
  long-running use, or the production 4.6-to-4.9 regression tests.
- RX 7900 XTX has no collected 0.3.1 rerun; this is a remaining hardware check,
  not a new prerequisite for starting integration.

Sanitized public record: https://github.com/misyaguziya/VRCT/issues/128

The handoff, NVIDIA validation summary and Claude implementation request are
saved in the repository's docs directory. Raw volunteer reports, local runtime
logs, model weights, vendor DLLs and distribution ZIPs are outside this source
snapshot. The bundled synthetic utterance remains a required diagnostic asset.

The sections below preserve the verification history at each earlier stage;
statements about pending hardware checks refer to those stages unless noted.

---

# Verification — COMGR cache workaround 0.3.1 (2026-11-19)

## Result

The CT2 child-process workaround, applied-state reporting, comparison gating,
independent rereview and updated distribution are complete. Required local
checks and release-package functional probes pass.
The new package is `native/target/amd-check-package-v3.1/vrct-amd-check/`
(4973 MiB). All v0.1, v0.2 and v0.3.0 package directories were preserved.
The report schema remains 3 and the diagnostic version is 0.3.1.

## Changes verified

### Japanese documentation and distribution ZIP (2026-11-19)

Added `README.ja.md` and `はじめに.txt` to the source and package; the English
README links to both. The packaging script retains them on future assembly.
Its UTF-8 BOM was checked with PowerShell 5.1 and 7 parsers so the Japanese
filename is interpreted correctly. Independent documentation rereview is LGTM.

The complete distribution ZIP is
`native/target/amd-check-package-v3.1/vrct-amd-check-0.3.1-windows-x64.zip`:

- Archive size: 4,020,130,885 bytes; uncompressed files: 5,214,427,778 bytes.
- SHA-256: `89bb1a6eb0026e22c5f0b8b1f034c5a9d06669da0efb036b32826329d2cd2d30`.
- All 2030 files match the package manifest and pass full CRC reads with Python's
  independent ZIP reader. The Japanese filename is explicitly stored as UTF-8.
- Packaged exe, both adapters and both Whisper model fingerprints remain the
  validated 0.3.1 values. No local test reports or symlinks are included.
- The ZIP has one `vrct-amd-check/` root folder. A `.zip.sha256` sidecar is next
  to it. Verification evidence is under the ignored
  `vrct-amd-check/target/zip-distribution-0.3.1/` folder.

No runtime code or binaries changed for this documentation/archive task, so the
successful runtime checks below were not repeated.

### Runtime workaround

- `main::supervise` supplies `AMD_COMGR_CACHE=0` to every `ct2-*` child,
  including imports, compute-type queries, CPU, Whisper, NLLB and concurrent
  probes. An inherited conflicting value is overridden only in that command.
- After the Job Object handshake and before dispatch can load vendor DLLs, the
  child checks for the exact value `0`, writes a fixed confirmation marker and
  flushes stderr. An incorrect value fails before vendor loading.
- Every supervised CT2 result records `data.ct2_comgr_cache`, including failed
  startup, crashes and timeouts. Configured value is distinct from observed
  state. Missing/malformed/duplicate observations give `observed_disabled:null`
  and `verified_before_vendor_load:false`; an explicit negative observation
  gives false. An unverified OK becomes FAIL. A verified startup never converts
  a failed inference into OK. Skipped workers have no applied-state record.
- JSON and text use the same Check data, so both reports retain the policy,
  scope, reason and confirmation. The benchmark contract records the disabled
  CT2 cache policy, and a matched comparison additionally requires the actual
  CT2 startup confirmation. Older or unverified results cannot be ranked.
- Parent/HIP/Vulkan processes and persistent Windows settings are unchanged.
  Models, precision, native adapter protocols, common mel and decoder settings
  are unchanged. No vendor DLL replacement or automatic retry was added.

## Commands and outcomes

Commands ran offline in the isolated `rust-p3-amd-spike/native/` worktree using
the existing MSVC/Ninja setup. Only the diagnostic runtime and documentation
were changed; the app crates were not modified.

| Check | Result |
| --- | --- |
| `cargo fmt -p vrct-amd-check -- --check` | PASS |
| `cargo test -p vrct-amd-check`, adapters disabled | PASS: 29 passed, 0 failed |
| Same test command, both adapters enabled / ROCm CT2 DLL | PASS: 29 passed, 0 failed |
| `cargo clippy -p vrct-amd-check --all-targets -- -D warnings` | PASS |
| `cargo clippy --workspace --all-targets -- -D warnings` | PASS |
| `cargo build --release -p vrct-amd-check`, both adapters / ROCm CT2 | PASS |
| `package.ps1` AST and full pinned package assembly | PASS |
| Package exe/adapters vs final build hashes, README and required assets | PASS |
| Independent implementation rereview | LGTM, no high/medium findings |

New tests run a real isolated child with a conflicting value of `1`, verify
that it receives `0`, and preserve the confirmation through an intentional
`0xC0000409` exit. Tests also cover non-CT2 scope, spawn-failure metadata,
unobserved/negative/malformed/duplicate observations and JSON/text reporting.
The existing comparison fixture now has 20 rejection cases, including missing,
negative or incorrectly configured cache-policy evidence. Existing timing,
common-feature, isolation and duration tests continue to pass.
Workspace Clippy used the previously documented temporary junction repair; the
original `native/third_party` junction was restored and the backup is absent.

## Release-package functional probes

The final distribution itself was used. The public CLI was launched with an
inherited `AMD_COMGR_CACHE=1` in an isolated test folder. Both CT2 import and
compute-query children reported configured value `0`, observed disabled true,
and verification before vendor load true in JSON and text. The import check
passed; the query failed on this non-AMD host and remained FAIL with its
startup evidence intact. Skipped and non-CT2 branches have no applied record.
The short custom WAV prevented unrelated inference during this report probe.

A directly launched internal CT2 child with cache value `1` failed with the
required-environment error before DLL loading. A correctly configured CT2
CPU float32 worker using the packaged ROCm DLL and pinned FP16 model completed
one warmup plus three measured requests. A non-CT2 whisper.cpp Vulkan worker
inheriting value `1` also completed one warmup plus three measured requests on
the local NVIDIA GeForce RTX 2080 Ti, without a CT2 policy marker.

All eight real-model outputs were exactly `Hello, how are you today?`, both
workers exited normally and shared the common feature SHA-256
`bf912b8bd3ea22ea48fb220e67062137bcb44bc286210cbe8d3b5908e7756aea`.
Probe evidence is kept in ignored
`vrct-amd-check/target/comgr-workaround-selftest/{check.py,results.json}` and its
`report-package/` folder. These local reports are not in the distribution.

## Distribution fingerprints and remaining hardware check

| File | SHA-256 |
| --- | --- |
| `vrct-amd-check.exe` | `96ef447a65d0a4c3546075b304aecf0230fc6e243942e38943fb4268d03840ed` |
| `vrct_ct2_49_adapter.dll` | `fa742c1b9ce1031cbf9daa415d3525400f054cfce764e34a4cc455b0786e04e3` |
| `whisper-vulkan/vrct_whisper_184_adapter.dll` | `40d18afec3c783fcc822b1c72e03ca6bf6a34a65f5fcf03dc296e91cdad6a7dc` |

The original investigation reproduced the identical LLVM fatal message and
`0xC0000409` using the packaged COMGR DLL alone, a non-ASCII cache path and
gfx1100-target compilation without GPU execution. ASCII paths or cache disabled
succeeded; a recent pruning timestamp temporarily hid the failure. Evidence:
`target/comgr-cache-investigation/run-389c262d88/results.json`. The vendor DLL
remains unchanged (SHA-256
`bd93c4545b5a1e325fb4dca029bdc36f64d08a57c21f41828603bef6001e244a`).

AMD GPU FP16 inference, resolution on the affected volunteer PC and the effect on warmed
inference latency remain untested locally. Cache disabling can increase compile,
load and warmup time; zero performance impact is not claimed. The complete
0.3.1 package must be rerun on the affected AMD machine. No commit, push,
public upload or permanent system environment change was performed.

---

# Historical 0.3.0 verification (superseded by workaround 0.3.1)

## Result

Both follow-up issues are fixed: the diagnostic enforces a 0.2-second minimum
and supplies the same prepared mel values to CT2 and whisper.cpp. Required local
checks, two independent reviews and real-model functional probes pass.
The updated distribution is assembled under
`native/target/amd-check-package-v3/vrct-amd-check/` (4973 MiB).
The v0.1 and v0.2 package directories and volunteer reports were preserved.

## Changes verified

- Accept only 3200..480000 samples of 16 kHz mono PCM16 (0.2..30 seconds).
  Both RIFF data size and decoded sample count are checked. Common-mel creation
  and the native adapter also enforce these limits; audio is never silently
  extended or truncated to satisfy the input limits.
- Both workers call the same Rust `PreparedMel::from_audio`. The existing
  Slaney frontend, normalization and feature-domain zero padding produce an
  immutable row-major float32 `[128, 3000]` buffer. CT2 models with other mel
  counts and Whisper models incompatible with this geometry are rejected.
- CT2 receives the prepared values directly. Whisper adapter protocol 2 copies
  those values with `whisper_set_mel` and calls `whisper_full(nullptr, 0)` on the
  same model for warmup and each measured request. The PCM-to-mel API is gone.
  The original sample count remains separate from padded geometry;
  `duration_ms = original_samples / 16` preserves it at the API's millisecond
  precision. A failed prepare clears the prepared flag before validation.
- The upstream v1.8.4 source was checked: set_mel copies the row-major values;
  original duration and single-segment/no-timestamp decoding do not change the
  encoder's full 3000-frame input. This avoids the previous frontend difference
  between feature padding and PCM padding.
- Each worker hashes all final float32 little-endian values and records frontend
  ID, shape, layout, dtype, original samples, duration and valid mel frames.
  The supervisor independently prepares expected metadata once outside timing.
  Both workers must match this entire record. Two matching but incorrect worker
  declarations cannot authorize a ratio.
- Report schema is 3 and timing scope is `resident_common_mel_to_utf8_v2`.
  Old contracts or protocol-1 Whisper adapters cannot enter the matched pair.
  Model hashes, effective compute type, physical GPU identity, normal exit,
  output consistency and complete sample/statistics checks remain required.
- Model load, WAV/mel preparation, input hashing and warmup are outside timing.
  Timed requests still run encoder through completed UTF-8 output on a resident
  model. This measures inference from common mel; it does not compare stock
  frontend speed/quality or promise identical internal arithmetic.

## Commands and outcomes

All Cargo commands ran offline from the isolated `rust-p3-amd-spike/native/`
worktree using the prepared MSVC/Ninja environment. Source remained unchanged
during independent validation. Both adapters in the final release were built
against the packaged ROCm CT2 DLL and pinned whisper.cpp v1.8.4 headers/DLL.

| Check | Result |
| --- | --- |
| `cargo fmt -p vrct-amd-check -- --check` | PASS |
| `cargo test -p vrct-amd-check`, adapters disabled | PASS: 26 passed, 0 failed |
| Same test command, both adapters enabled / ROCm CT2 DLL | PASS: 26 passed, 0 failed |
| `cargo clippy -p vrct-amd-check --all-targets -- -D warnings` | PASS |
| `cargo clippy --workspace --all-targets -- -D warnings` | PASS |
| `cargo build --release -p vrct-amd-check`, both adapters / ROCm CT2 | PASS |
| Native C++ mel-input and token-budget boundary compile/run | PASS, also executed directly after build |
| `package.ps1` PowerShell AST and complete package assembly | PASS |
| Packaged exe and both adapter hashes vs final build | PASS |
| Required package entries, notices and absence of CUDA DLLs | PASS |
| Independent backend/input parity review | LGTM, no remaining high/medium issues |
| Independent comparison/metadata gate review | LGTM, no remaining high/medium issues |

Duration tests include 0, 1, 200, 1600, 3199, 3200, 3201, 480000 and 480001
samples. Common-mel tests cover both accepted endpoints, retained original
length, nonfinite rejection and hashing the final padded value. Seventeen
comparison failure cases include missing/different metadata, both workers
sharing a false digest, wrong dtype/shape/sample count and an old timing scope.
Native checks additionally cover null pointers, count/geometry mismatch and
NaN/Inf. The original broken `native/third_party` junction was temporarily
substituted only for workspace Clippy, then restored in a finally block and
verified; the temporary backup is absent. See historical notes for provenance.

## Real-model probes on the updated distribution

The final AMD package itself was used for the following deadline-bounded
probes. These are functional checks on a host with an NVIDIA GeForce RTX 2080
Ti, not AMD performance measurements.

| Probe | Warmup + timed requests | Transcript / exit |
| --- | --- | --- |
| Packaged CT2 4.9 ROCm DLL, CPU float32, pinned FP16 model | 1 + 3 | All correct, exit 0 |
| Packaged whisper.cpp 1.8.4 CPU, pinned FP16 model | 1 + 3 | All correct, exit 0 |
| Packaged whisper.cpp 1.8.4 Vulkan, local NVIDIA GPU | 1 + 3 | All correct, verified Vulkan backend, exit 0 |

All twelve outputs were exactly `Hello, how are you today?`. All three workers
reported the same metadata, including SHA-256
`bf912b8bd3ea22ea48fb220e67062137bcb44bc286210cbe8d3b5908e7756aea`,
shape `[128, 3000]`, 41040 original samples, 2565 ms and 257 valid mel frames.
Normal exits cover model destruction and DLL shutdown.

Additional release-binary checks passed:

- Loading the old v0.2 protocol-1 Whisper adapter returns FAIL with the protocol
  error before the changed prepare function is invoked.
- Native CPU model: prepare valid input, then reject short/wrong-shape/NaN
  input; transcribe fails immediately instead of reusing the previous mel.
  A subsequent valid prepare and model destruction both succeed.
- A 3199-sample custom WAV supplied through the public CLI is reported FAIL
  with the 0.2..30-second requirement; no inference succeeds. The resulting
  report identifies diagnostic 0.3.0 and schema 3.

Local probe harness and evidence are kept in the ignored
`vrct-amd-check/target/common-mel-selftest/{check.py,results.json}`.
These files and local NVIDIA probe reports are not placed in the distribution.

## Distribution fingerprints and remaining hardware check

| File | SHA-256 |
| --- | --- |
| `vrct-amd-check.exe` | `6d1f50ee005a6451237349edf3352900e3fe94bd65d19f230ea78d183f772e67` |
| `vrct_ct2_49_adapter.dll` | `617f93a8f6a4fa7b7abc2c242e95e2767a1d722426d3e0de451c8f70b763c84a` |
| `whisper-vulkan/vrct_whisper_184_adapter.dll` | `c3c7efda5b786bfed7ef044c08be36f7a4f8e86b57130786f5e9df8fa31723a6` |

AMD GPU inference/performance for 0.3.0 remains untested on this host. The RX
7800 XT and RX 9070 XT volunteers need to run the complete updated package.
Their previous 0.1 results, and the 0.2 timings with different frontends, cannot
be reused as the new common-mel comparison. No commit, push or public upload
was performed.

---

# Historical 0.2.0 verification (superseded by common-mel 0.3.0)

## Result

The changed diagnostic passes its local required checks and independent review.
The new AMD package is assembled under
`native/target/amd-check-package-v2/vrct-amd-check/` (4973 MiB).
Its executable SHA-256 is
`2392c6fed4b25e5f8747eeb9f4a1dc4e123ac7b44851f023ff7866c97f9a69d0`.
The original v0.1 package and received volunteer reports were preserved.

## Changes verified

- whisper.cpp v1.8.4 DLL context and prepared mel persist across one warmup and
  all timed requests. The timer encloses inference through UTF-8 text retrieval.
- Both engines use greedy beam 1, temperature 0, four threads, English,
  no history/timestamps/VAD/temperature fallback/Flash Attention, and a matched
  128-step generation budget (including EOT).
- The CT2 adapter protocol is 2. Old protocol-1 adapters are rejected.
- Actual model/tokenizer/config SHA-256 values must match the pinned FP16 pair.
  Unknown or old quantized models remain diagnostic inputs but cannot be ranked.
- Both best and median are reported; cross-engine ranking uses the median.
  Missing, failed, different-device/precision/contract/quality measurements do
  not produce a cross-engine ratio. CLI process wall time is never a substitute.
- CPU comparison uses CT2 float32 expanded from FP16 weights, versus native
  whisper.cpp CPU kernels with FP16 weights. Internal arithmetic/layout parity
  is not claimed. INT8 modes and NLLB remain separate diagnostic cases.

## Commands and outcomes

All Rust commands ran from the isolated `rust-p3-amd-spike/native/` worktree,
with Cargo offline. MSVC, Ninja and cached dependencies were used.

| Check | Result |
| --- | --- |
| cargo fmt -p vrct-amd-check -- --check | PASS |
| cargo test -p vrct-amd-check, adapters disabled | PASS: 23 passed, 0 failed |
| cargo test -p vrct-amd-check, adapters enabled, final token fix | PASS: 23 passed, 0 failed |
| cargo clippy -p vrct-amd-check --all-targets -- -D warnings | PASS |
| cargo clippy --workspace --all-targets -- -D warnings | PASS |
| cargo build --release -p vrct-amd-check, both adapters / CUDA CT2 | PASS |
| cargo build --release -p vrct-amd-check, both adapters / packaged ROCm CT2 | PASS |
| Native C++ token-budget boundary compile/run, through build.rs | PASS |
| package.ps1 PowerShell AST | PASS |
| package.ps1, complete pinned FP16 package | PASS |
| Independent static review, including token-cap follow-up | LGTM; no remaining high/medium issues |

The native token-budget regression covers 127 text tokens plus EOT at the
128-step boundary, rejects 128 steps without EOT and 129 steps with EOT.
v1.8.4 uses a zero-based stopping index; the adapter sets 127 for that budget.
MSVC `/utf-8` is required for the test source and adapter comments.
The existing upstream CT2 header emits C4244; Rust/Clippy checks pass with
`-D warnings`.

Workspace Clippy initially encountered an existing broken `native/third_party`
junction and missing core CT2 4.6 headers. For that check only, the original
junction was renamed and a temporary junction referenced already prepared root
checkout assets. Matching 4.6 headers were extracted from the existing verified
cache into this diagnostic's ignored target folder, with CT2_INCLUDE_DIR/DLL_DIR
overrides. The original junction was restored in a finally block and verified.
No app source, reference data, shared DLLs or original junction target changed.
The diagnostic itself does not depend on that app-assets junction.

Build inputs for the check adapters were official CT2 4.9.0 headers and either
its CUDA self-test DLL or the exact ROCm DLL in the pinned release cache;
whisper headers were the hash-checked lemonade-sdk v1.8.4 files. The Windows
Vulkan release DLL/archive was already cached. No handwritten Whisper structs
or app CT2 4.6 ABI were used by the new worker.

## Real-model functional probes

Prepared the verified unquantized FP16 pair (actual checksums validated) and ran
separate deadline-bounded child workers. These are functional checks, not AMD
performance results; other build/copy activity was running on this machine.

| Probe | Warmup + timed requests | Transcript / exit |
| --- | --- | --- |
| CT2 4.9 CUDA DLL, CPU float32, FP16 saved model | 1 + 3 | All correct, exit 0 |
| whisper.cpp 1.8.4 CPU, FP16 model | 1 + 3 | All correct, exit 0 |
| whisper.cpp 1.8.4 Vulkan, local NVIDIA GPU, FP16 model | 1 + 3 | All correct, actual Vulkan backend, exit 0 |
| Complete AMD package's ROCm CT2 DLL, CPU float32, FP16 saved model | 1 + 1 | Both correct, exit 0 |

Every transcript was exactly `Hello, how are you today?`. Normal process exits
also passed model destruction and DLL shutdown. Probe JSON is kept under the
ignored diagnostic target folder (`aligned-selftest/resident_smoke.json` and
`rocm_cpu_smoke.json`). The AMD package contains the 118549504-byte ROCm CT2 DLL
and no CUDA/cuBLAS/cuDNN DLLs; adapter/executable hashes were checked after copy.

## Limits and next hardware run

AMD GPU inference for **0.2.0** is not tested on this NVIDIA host. CT2 GPU timing
was not measured locally. The earlier RX 7800 XT / RX 9070 XT results use 0.1.0
and cannot be relabelled as the new matched benchmark. Volunteers must run the
complete new package, including both FP16 model formats and both new adapters.
The tool blocks uncertain rankings instead of filling missing values from old
CLI totals. Long-term/VRChat load, multiple physical HIP GPUs, multilingual and
real microphone quality still require the corresponding hardware/input tests.
No commit, push, public upload, automation or app integration was performed.

---

## Historical 0.1.0 verification (superseded for the current benchmark)

# Verification — 2026-11-18

## Check-only CT2 4.9.0 adapter update

Scope of this update: native/vrct-amd-check/ and its native/Cargo.lock dependency
entry only. The app's vrct-ct2 source/build was not changed. No commit, push,
branch switch, download, GPU inference or maintainer self-test was performed.

The optional build creates vrct_ct2_49_adapter.dll using VRCT_CT2_49_INCLUDE
(the include/ folder in the official v4.9.0 source tree; its parent CMakeLists.txt
version is checked) and VRCT_CT2_49_DLL_DIR (the matching Windows x64 CT2 DLL).
No CT2 import library is linked into the supervisor. All CT2 calls, including
compute capabilities, are inside handshake-gated, deadline-supervised children.

Without VRCT_CT2_49_INCLUDE, both requested CT2 stage groups report exactly:
"skipped: built without the 4.9.0 adapter". Rust bindings, input preparation and
stage orchestration are still compiled and linted in this configuration.

### Current verification

PowerShell launched Cargo with ProcessStartInfo.WorkingDirectory set to native/.
Both VRCT_CT2_49_INCLUDE and VRCT_CT2_49_DLL_DIR were removed from the child
environment. CARGO_NET_OFFLINE=true prevented downloads. The existing in-crate
target directory, short-path junction and Ninja/CMake setup described below were
reused; temporary build files remained under vrct-amd-check/target/.

| Command | Result |
| --- | --- |
| cargo fmt -p vrct-amd-check | PASS |
| cargo test -p vrct-amd-check | PASS: 20 passed, 0 failed, 0 ignored |
| cargo clippy --workspace --all-targets -- -D warnings | PASS: exit 0, zero Rust/Clippy warnings |

The tool launcher also prints "warn: could not canonicalize path D:\WORKSPACE".
This is an environment/launcher message, not a Cargo/Clippy diagnostic.

Added behavior coverage: capability combinations, absent-adapter SKIPs and stage
limits, query-failure gating, all ten inference workers including CPU continuation
after GPU failure, ratio omission for failed measurements, valueless non-ROCm
flag parsing/serialization, NLLB prefix/EOS/decoding, and finite 80/128-mel
features/windows from the embedded utterance. Existing process crash, timeout,
bounded capture, PE, redaction and Vulkan tests also pass.

Independent static review found no high/medium issues. Review suggestions led to
the explicit source-version guard, kernel32.lib in the adapter link and the
additional orchestration/preprocessing tests.

### Not verified in this update

No 4.9.0 headers or CT2 DLL were downloaded or supplied for this run. Therefore
the enabled C++ compile/link path, actual exported C++ ABI compatibility,
adapter DLL loading, model output quality, GPU/CPU timings and shared-model
execution are **not runtime-verified**. Neither NVIDIA nor AMD inference has been
claimed as tested. Source-version declarations do not validate binary provenance
or guarantee a compatible MSVC/STL/CRT. Use the exact build/package/NVIDIA command
in README.md for the maintainer's next step.

Whisper preprocessing reuses the app algorithm with scalar matrix accumulation,
so it is not a bit-for-bit OpenBLAS parity test. Stage C uses a bounded short
English transcription path and fixed English-to-Japanese NLLB input. Semantic
quality remains a manual check. NVIDIA self-test reports are explicitly not AMD
verification.

---

## Historical initial diagnostic verification (before this update)

Scope: new vrct-amd-check crate, native/Cargo.toml workspace membership and the
new package entry in native/Cargo.lock. No app crate, third_party junction,
VRCT configuration, branch, commit or remote was changed.

## Results

All Cargo commands were launched from PowerShell with the actual process working
directory set to native/. CARGO_NET_OFFLINE=true was used throughout.

| Exact command | Result |
| --- | --- |
| cargo test -p vrct-amd-check | PASS: 13 passed, 0 failed, 0 ignored |
| cargo clippy -p vrct-amd-check --all-targets -- -D warnings | PASS, exit 0 |
| cargo clippy --workspace --all-targets -- -D warnings | PASS, exit 0; final run 3m 21s |
| cargo build --release -p vrct-amd-check | PASS |
| cargo rustc --release -p vrct-amd-check -- -C target-feature=+crt-static | PASS; this is the delivered executable |
| vrct-amd-check\run\vrct-amd-check.exe --runs 1 --timeout 60 | PASS: exit 0, no parent crash, both reports written |
| git diff --check | PASS |

The diagnostic's unit tests exercise a real Windows kernel32.dll, PE regular and
delay imports/truncation/build identity, redaction and valid JSON, stage gating
and report wording, bundled speech, local-only inputs, Vulkan fallback detection,
bounded logs, crash exit codes, and a hanging grandchild whose partial output
must survive termination and remain redactable.

Independent review: LGTM after fixes to local-path filtering, supervised
environment inventory and lossless streaming of child output. No outstanding
high/medium findings. No AMD or upstream Vulkan inference was claimed as tested.

## Build environment adjustments

Tests and the release executable used:

~~~powershell
$env:CARGO_TARGET_DIR = '<worktree>\native\vrct-amd-check\target'
$env:CARGO_NET_OFFLINE = 'true'
~~~

Workspace Clippy first stopped in the pre-existing sentencepiece-sys dependency:
the sandbox denied MSBuild's user-SDK lookup. Installed Ninja avoided that
lookup, but CMake's default Debug compiler check hit a resource-compiler error,
and long generated object paths then exceeded the Windows path limit.

The final successful run used only in-crate generated build configuration:

~~~powershell
$env:CMAKE_GENERATOR = 'Ninja'
$env:PATH = 'C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;' + $env:PATH
$env:CMAKE_TOOLCHAIN_FILE = '<worktree>\native\vrct-amd-check\target\try-release.cmake'
$env:CARGO_TARGET_DIR = 'D:\WORKSPACE\WORK\VRChatProject\VRCT\CLAUDE~1\WORKTR~1\RU2D97~1\native\VRCT-A~2\t'
cargo clippy --workspace --all-targets -- -D warnings
~~~

The ignored t/ junction points to the same crate's target/ninja/ directory.
The displayed short path is specific to this machine, not a portable build
requirement. No directories were moved or third-party sources edited.

The generated toolchain contains:

~~~cmake
set(CMAKE_TRY_COMPILE_CONFIGURATION Release)
set(CMAKE_C_COMPILER "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/HostX64/x64/cl.exe")
set(CMAKE_CXX_COMPILER "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/HostX64/x64/cl.exe")
~~~

Because the existing CMakeSystem.cmake predated the toolchain setting, its
generated CMakeCache.txt was also given
CMAKE_TRY_COMPILE_CONFIGURATION:STRING=Release, and its output-directory
prefix was updated to the short alias. Compiler and linker checks were retained;
no compiler-success or ABI-result variables were forced.

Final workspace Clippy had no Rust/Clippy warnings. The sandbox's tool launcher
still printed "warn: could not canonicalize path D:\WORKSPACE"; this is separate
from the lint result. The final captured build log is in ignored
target/workspace-clippy.log.

## Local execution

The final static-runtime executable is in run/vrct-amd-check.exe (ignored).
dumpbin /dependents lists only:

~~~text
kernel32.dll
api-ms-win-core-synch-l1-2-0.dll
bcryptprimitives.dll
ntdll.dll
~~~

No CT2/HIP DLL, app DLL or VCRUNTIME140.dll is needed to start the supervisor.

Actual report excerpt:

~~~text
[WARN] GPU inventory (optional) -- Windows video controllers and driver versions.
[OK  ] Bundled utterance -- Synthetic speech: Hello, how are you today?
[FAIL] Stage A: HIP runtime -- No HIP runtime found.
[SKIP] Stage A: hipBLAS -- HIP prerequisite failed.
[SKIP] Stage B: CTranslate2 PE imports -- Stage A did not pass, or --stage a was requested.
[SKIP] Stage C: Whisper, NLLB and concurrent use -- Earlier ROCm prerequisite did not pass.
[SKIP] Part 2: whisper.cpp -- Upstream Vulkan binary is absent. Nothing was downloaded.
[SKIP] Part 2: llama.cpp -- Upstream Vulkan binary is absent. Nothing was downloaded.
Reports written next to this exe. Please read both before sharing.
~~~

This is the user-described NVIDIA/no-AMD machine. Optional WMI inventory was
denied by the sandbox (HRESULT 0x80041003), so the diagnostic itself did not
confirm the GPU's model name. Raw localized OS error text is preserved verbatim.
The meaningful acceptance result is graceful completion with no HIP runtime and
independent Vulkan skips.

run/vrct_amd_check_report.txt and run/vrct_amd_check_report.json were generated.
The JSON parses successfully; neither report contains the current username/home.

## Historical remaining prerequisites (superseded by the adapter update above)

At the time of the initial diagnostic, CT2 supported-compute-type queries and all Stage C operations are intentionally
unimplemented/blocked by the 4.6.0 versus 4.9.0 ABI prerequisite, as permitted by
the task. A validated adapter built with the supplied 4.9.0 ROCm DLL's exact
headers/toolchain is needed before implementing those workers. A crash-isolated
4.6 shim would not be valid evidence.

The maintainer must pin/package the upstream Vulkan releases and their DLLs,
compatible GGML/GGUF models, intended CT2/NLLB models/tokenizers, the ROCm DLL and
its HIP/rocBLAS assets. README.md has placeholders and layout instructions.
AMD hardware, real Vulkan inference, timing/quality comparisons, and the
gfx1201/concurrent-CT2 checks remain unverified.
