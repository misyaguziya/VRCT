# CTranslate2 ROCm Windows shutdown hang

## Summary

The official CTranslate2 4.8.2 ROCm Windows wheel hangs during process
shutdown after a CPU inference. The same model and Python process using the
standard CTranslate2 4.8.2 wheel exits normally. No Radeon GPU is required.

```powershell
$model = (Resolve-Path 'src-python\weights\ctranslate2\nllb-200-distilled-600M-ct2-int8').Path
.\tools\ct2_compare\run_probe.ps1 `
  -Python '.venv_ct2_482_rocm\Scripts\python.exe' -Model $model
```

Observed output from the ROCm wheel:

```text
version=4.8.2
device=cpu
loading
unload_begin
delete_begin
delete_ref_done=0.000
gc_done=0.000
```

The child process did not exit within 180 seconds and had to be terminated by
`run_probe.ps1`, which returns exit code 124 on timeout.

Control with the standard 4.8.2 wheel and the same model:

```text
version=4.8.2
device=cpu
loading
loaded
inference
inference_done
unload_begin
unload_done=0.203
delete_begin
delete_ref_done=0.000
gc_done=0.000
exit=0
```

The standard wheel took 97.016 seconds in this single CPU run because the
local model is large; it nevertheless exited with code 0. Without inference,
the trigger after native inference state is created, but does not distinguish
the HIP runtime, native worker, or DLL detach path.

## Related upstream runtime fix

PyTorch issue #160759 tracks the same Windows ROCm teardown hang and records a
root fix in `ROCm/rocm-systems#3790` (also referenced by the later `#8479`
change). The reported root cause is `__hipUnregisterFatBinary` calling stream
teardown after Windows has already terminated the worker thread;
`Event::awaitCompletion()` could then wait forever.

The fix is present in ROCm nightly versions at or after `7.13.0a20260312`.
CTranslate2 4.8.2's official Windows wheel is built with the ROCm 7.2 line,
so its bundled `amdhip64_7.dll` predates this fix.

### A/B result with the prebuilt runtime patch

The prebuilt test DLL from `dixieclick/rocm-systems` release
`amdhip64-pr3656` was tested in the isolated `.venv_ct2_482_rocm` environment.

```text
patched DLL SHA-256:
39b73ac4061e5b182f7c9ee85f5d3c7211aa895fc6dbda8bd17a06dd0f00b2a3

ROCm wheel, CPU model, no inference:  exit=0
ROCm wheel, CPU inference completed:  timeout=180s, exit=124
```

The runtime patch therefore does not fix this CTranslate2 reproducer. It may
still fix GPU-work teardown cases, but that requires a Radeon GPU test. The
original `amdhip64_7.dll` was restored after the A/B test.

The ROCm DLL directly imports:

```text
hipblas.dll, amdhip64_7.dll, KERNEL32.dll, MSVCP140.dll, libiomp5md.dll,
VCRUNTIME140.dll, VCRUNTIME140_1.dll
```

The ROCm DLL is approximately 277 MB, versus approximately 58 MB for the
standard build. The tested wheel is the CTranslate2 v4.8.2 release asset:

```text
ctranslate2-4.8.2-cp311-cp311-win_amd64.whl
archive SHA-256:
43da4baa5feaee49f77e176277a9647f99c493173c81a0bc60f491cac97532c2
ctranslate2.dll SHA-256:
37fdba6e52f87422562f7068c7bc19e342d57bf957a161da6d9fdf6d47f93317
```

## Source inspection

The v4.8.2 source already joins CTranslate2 worker threads in
`ThreadPool::~ThreadPool()`, synchronizes the device while destroying a model,
and frees thread-local curand/hiprand states in `destroy_context()`.

There is no ROCm-specific Windows process shutdown path. The same shutdown
code is present on upstream master commit
`d44d2d069eb88c7b7804da864c10c201501cb4a9` (checked 2026-09-23).

## Requested investigation

Please check whether the HIP Windows backend needs an explicit cleanup path
before DLL detach, especially for thread-local stream, allocator, or runtime
state created by an inference worker. A useful patch should be validated
against:

1. CPU device with the ROCm wheel, after one inference;
2. Radeon GPU device after one inference;
3. standard CPU/CUDA wheel regression;
4. repeated model creation and destruction in a single process.

The current report does not claim that repeated model switching or Radeon GPU
execution has been reproduced by this CPU-only harness.

## HIP DLL delay-load experiment

The candidate CMake patch added Windows linker delay-load entries for
`hiprand.dll`, `hipblas.dll`, and `amdhip64_7.dll`, plus `delayimp.lib`.

Results from a temporary Windows ROCm 7.2 build:

- build completed successfully;
- PE inspection showed none of the three HIP DLLs in the normal import table;
- loading the resulting DLL with `ctypes.CDLL` failed with Windows error 1114,
  both with and without the ROCm runtime directory visible;
- the build used the `gfx906` fallback because this machine has no Radeon GPU.

Removing normal PE imports is therefore not sufficient. HIP fat-binary
registration or another static initializer still appears to touch the runtime
at DLL initialization time. A complete solution may require separating the
CPU core and HIP kernels into different DLLs.

Adding `unload_model()` or Python `gc.collect()` alone is not sufficient for
this reproducer. `TerminateProcess` is only an emergency containment option,
not a normal cleanup fix.

## Candidate upstream patch result

The candidate patch added `synchronize_stream(_device)` before
`ReplicaWorker::_replica.reset()`.

- Windows ROCm 7.2 CTranslate2 build: compiled successfully;
- runtime effect on the CPU-only shutdown reproducer: **not established**;
- the CPU reproducer does not use a HIP stream, so this cannot explain the
  observed CPU-only ROCm DLL shutdown hang.

The next upstream investigation should target ROCm DLL/runtime process detach
or delayed HIP loading for CPU execution.