# HIP backend split design

## Finding

Windows `/DELAYLOAD` successfully removes `hipblas.dll`, `hiprand.dll`, and
`amdhip64_7.dll` from the normal PE import table in a temporary CTranslate2
ROCm build. However, the resulting DLL still fails at `ctypes.CDLL` with
`ERROR_DLL_INIT_FAILED` (1114), even when the ROCm DLL directory is visible.

This indicates that HIP fat-binary registration or another HIP static
initializer runs while `ctranslate2.dll` is loaded. Delay-loading the import
libraries alone does not guarantee CPU-only initialization is independent from
HIP.

## Required architecture

```text
ctranslate2.dll       CPU core and public C++/Python-facing symbols
ctranslate2_hip.dll   HIP kernels, hipblas/hiprand dependencies, HIP init
```

The Python extension should load the CPU core unconditionally and load the HIP
backend only when a CUDA-device CTranslate2 object is first constructed.
`device="cpu"` must never load `ctranslate2_hip.dll`.

## Constraints

- Keep the public Python API unchanged (`device="cuda"` remains the ROCm API
  spelling used by the existing wheel).
- Do not call `hipInit`, load HIP DLLs, or register HIP fat binaries on
  CPU-only paths.
- Keep CUDA and ROCm backend selection separate at build/package time.
- Provide a CPU-only regression that imports and runs a model with no ROCm DLLs
  present.
- Provide a GPU regression that loads the HIP backend on first GPU use.

## Why not just delay-load

`/DELAYLOAD` changes the PE import table, but HIP device compilation can emit
module registration code that executes during DLL initialization. The observed
1114 failure after PE delay-load confirms that this distinction matters.

## Upstream request

Ask CTranslate2 upstream whether the HIP backend can be built as a load-on-use
plugin, or whether the Python wheel should ship separate CPU and ROCm native
extensions. The delay-load experiment is evidence, not a complete fix.