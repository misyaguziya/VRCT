# 協力者に渡す一式を native/target/amd-check-package-v3.1 に組み立てる (メンテナー用)。
# 取得するものは版と SHA-256 を固定し、合わないものは使わない。HIP の DLL とカーネルは、この PC に
# 入れた AMD HIP SDK 7.2 から写す。4.9.0 のアダプター付きの exe を先にビルドしておくこと (README の Build)。
# 翻訳用の HY-MT1.5 (GGUF) は地域の制限 (EU・英国・韓国では使えない) があるので、一式には入れない。
param(
    [string]$HipSdk = 'C:\Program Files\AMD\ROCm\7.2',
    [string[]]$Gfx = @('gfx1100', 'gfx1101', 'gfx1102', 'gfx1103', 'gfx1150', 'gfx1151', 'gfx1200', 'gfx1201')
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$native = Split-Path $PSScriptRoot -Parent
$src = Join-Path $native 'target\amd-check-src'
$out = Join-Path $native 'target\amd-check-package-v3.1\vrct-amd-check'
New-Item -ItemType Directory -Force $src | Out-Null
$allowed = [IO.Path]::GetFullPath((Join-Path $native 'target')) + [IO.Path]::DirectorySeparatorChar
if (-not ([IO.Path]::GetFullPath($out)).StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) { throw 'Package output must stay inside native/target' }
if (Test-Path -LiteralPath $out) { Remove-Item -LiteralPath $out -Recurse -Force }
New-Item -ItemType Directory -Force $out | Out-Null

function Get-Pinned([string]$name, [string]$url, [string]$sha256) {
    $file = Join-Path $src $name
    if (-not (Test-Path $file)) {
        New-Item -ItemType Directory -Force (Split-Path $file) | Out-Null
        Invoke-WebRequest $url -OutFile $file
    }
    $actual = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $sha256) { Remove-Item $file; throw "${name}: SHA-256 $actual != $sha256" }
    $file
}
function Expand-To([string]$zip, [string]$dir) {
    $dir = [IO.Path]::GetFullPath($dir)
    $tmp = [IO.Path]::GetFullPath("$dir.tmp")
    foreach ($path in @($dir, $tmp)) {
        if (-not $path.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) { throw 'Archive output must stay inside native/target' }
    }
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
    Expand-Archive $zip $tmp
    # 余分な 1 段 (bin/ など) は平らにする
    $inner = Get-ChildItem $tmp
    $root = if ($inner.Count -eq 1 -and $inner[0].PSIsContainer) { $inner[0].FullName } else { $tmp }
    New-Item -ItemType Directory -Force $dir | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $root) { Move-Item -LiteralPath $item.FullName -Destination $dir }
    Remove-Item -LiteralPath $tmp -Recurse -Force
}

# 1. 検証プログラム (4.9.0 のアダプター付き)
$build = Join-Path $native 'vrct-amd-check\target-49\release'
foreach ($f in 'vrct-amd-check.exe', 'vrct_ct2_49_adapter.dll') { Copy-Item (Join-Path $build $f) $out }
foreach ($document in 'README.md', 'README.ja.md', 'はじめに.txt', 'HIP-LICENSE.txt') {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $document) -Destination $out
}

# 2. CTranslate2 4.9.0 ROCm 版 (上流の Windows 用 wheel から DLL だけ)
$ct2zip = Get-Pinned 'ct2-rocm-windows.zip' 'https://github.com/OpenNMT/CTranslate2/releases/download/v4.9.0/rocm-python-wheels-Windows.zip' '99cbc7210f035d04ed2f38aa653e79b2b1dcc90cb7503af72d880785b66b7f84'
$whl = Join-Path $src 'ct2-rocm-cp311.whl'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$z = [IO.Compression.ZipFile]::OpenRead($ct2zip)
try { [IO.Compression.ZipFileExtensions]::ExtractToFile(($z.Entries | Where-Object Name -eq 'ctranslate2-4.9.0-cp311-cp311-win_amd64.whl'), $whl, $true) } finally { $z.Dispose() }
$w = [IO.Compression.ZipFile]::OpenRead($whl)
try {
    foreach ($e in $w.Entries | Where-Object { $_.FullName -match '^ctranslate2/[^/]+\.dll$' }) {
        [IO.Compression.ZipFileExtensions]::ExtractToFile($e, (Join-Path $out $e.Name), $true)
    }
    $lic = $w.Entries | Where-Object { $_.FullName -match 'LICENSE' } | Select-Object -First 1
    if ($lic) { [IO.Compression.ZipFileExtensions]::ExtractToFile($lic, (Join-Path $out 'CTranslate2-LICENSE.txt'), $true) }
} finally { $w.Dispose() }

# 3. HIP ランタイム・hipBLAS・rocBLAS・hipBLASLt (HIP SDK 7.2 から。RDNA3 / RDNA3.5 / RDNA4 のカーネルだけ)
$hip = Join-Path $out 'hip'
New-Item -ItemType Directory -Force $hip | Out-Null
foreach ($f in 'amdhip64_7.dll', 'amd_comgr_3.dll', 'hipblas.dll', 'rocblas.dll', 'hipblaslt.dll') { Copy-Item (Join-Path $HipSdk "bin\$f") $hip }
foreach ($lib in 'rocblas', 'hipblaslt') {
    $from = Join-Path $HipSdk "bin\$lib\library"
    $to = Join-Path $hip "$lib\library"
    New-Item -ItemType Directory -Force $to | Out-Null
    # GPU を名前に持たないカーネルは共通なので全部、持つものは対象の GPU の分だけ
    Get-ChildItem $from -File | Where-Object {
        $arch = [regex]::Match($_.Name, 'gfx\d+').Value
        -not $arch -or $Gfx -contains $arch
    } | Copy-Item -Destination $to
}
$licenses = Join-Path $hip 'licenses'
New-Item -ItemType Directory -Force $licenses | Out-Null
foreach ($d in 'hipblas', 'hipblas-common', 'hipblaslt', 'rocblas') {
    Copy-Item (Join-Path $HipSdk "share\doc\$d\LICENSE.md") (Join-Path $licenses "$d-LICENSE.md")
}

# 4. Vulkan 版の whisper.cpp と llama.cpp
Expand-To (Get-Pinned 'whisper-vulkan.zip' 'https://github.com/lemonade-sdk/whisper.cpp-rocm/releases/download/v1.8.4/whisper-v1.8.4-windows-vulkan-x64.zip' 'e0d20a0f92e31b98adc0faf71172efc810b701e6391a9d858ca045bff26f77cd') (Join-Path $out 'whisper-vulkan')
Expand-To (Get-Pinned 'llama-vulkan.zip' 'https://github.com/ggml-org/llama.cpp/releases/download/b12497/llama-b12497-bin-win-vulkan-x64.zip' '893b27c1db5841c19a8e366577b916aed3740aee9e601b3da2631b87e0c96f2c') (Join-Path $out 'llama-vulkan')
Copy-Item (Join-Path $build 'vrct_whisper_184_adapter.dll') (Join-Path $out 'whisper-vulkan')

# 5. モデル (版と SHA-256 は native/data/model_catalog.json と同じ)
$models = Join-Path $out 'models'
$hf = 'https://huggingface.co'
$turbo = @{ repo = 'deepdml/faster-whisper-large-v3-turbo-ct2'; rev = '4df90f75321148c3a29a9e2351b7ddf8f5b115a8'; files = @(
    @('config.json', 'b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e'),
    @('model.bin', 'e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da'),
    @('preprocessor_config.json', '7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711'),
    @('tokenizer.json', '297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd'),
    @('vocabulary.json', 'c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1')) }
$nllb = @{ repo = 'JustFrederik/nllb-200-distilled-600M-ct2-int8'; rev = '302d78f00e6fdb50a1064059df7c392b735e9d05'; files = @(
    @('config.json', '0c2f6fa2057c7264d052fb4a62ba3476eeae70487acddfa8e779a53a00cbf44c'),
    @('model.bin', 'ed1beaf75134de7505315a5223162f56acff397eff6b50638a500d3936fe707b'),
    @('sentencepiece.bpe.model', '14bb8dfb35c0ffdea7bc01e56cea38b9e3d5efcdcb9c251d6b40538e1aab555a'),
    @('shared_vocabulary.txt', 'a132a83330f45514c2476eb81d1d69b3c41762264d16ce0a7ea982e5d6c728e5'),
    @('special_tokens_map.json', '992bd4ed610d644d6823081937bcc91bb8878dd556cea4ae5327f2480361330e'),
    @('tokenizer.json', 'e316b82de11d0f951f370943b3c438311629547285129b0b81dadabd01bca665'),
    @('tokenizer_config.json', 'd1aa8c3697d3e35674f97b5b7e9c99d22b010f528e80140257d97316be90d044')) }
foreach ($m in @(@('whisper-ct2-fp16', $turbo), @('nllb-ct2', $nllb))) {
    $dir = Join-Path $models $m[0]
    New-Item -ItemType Directory -Force $dir | Out-Null
    foreach ($f in $m[1].files) {
        $file = Get-Pinned "models\$($m[0])\$($f[0])" "$hf/$($m[1].repo)/resolve/$($m[1].rev)/$($f[0])" $f[1]
        Copy-Item $file $dir
    }
}
Copy-Item (Get-Pinned 'models\ggml-large-v3-turbo.bin' "$hf/ggerganov/whisper.cpp/resolve/98aa99a0a9db05ae2342309f5096248665f7cba3/ggml-large-v3-turbo.bin" '1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69') $models

# 6. 配るものごとのライセンス文 (固定の版から) と、モデルの表示
$notices = Join-Path $out 'licenses'
New-Item -ItemType Directory -Force $notices | Out-Null
$raw = 'https://raw.githubusercontent.com'
foreach ($l in @(
        @('CTranslate2-LICENSE.txt', 'OpenNMT/CTranslate2/v4.9.0/LICENSE'),
        @('llama.cpp-LICENSE.txt', 'ggml-org/llama.cpp/b12497/LICENSE'),
        @('whisper.cpp-LICENSE.txt', 'lemonade-sdk/whisper.cpp-rocm/v1.8.4/LICENSE'),
        @('HIP-runtime-clr-LICENSE.md', 'ROCm/clr/rocm-7.2.0/LICENSE.md'),
        @('amd_comgr-LICENSE.txt', 'ROCm/llvm-project/rocm-7.2.0/amd/comgr/LICENSE.txt'))) {
    Invoke-WebRequest "$raw/$($l[1])" -OutFile (Join-Path $notices $l[0])
}
@'
Models in models/:
- whisper-ct2-fp16: deepdml/faster-whisper-large-v3-turbo-ct2 @ 4df90f75 (MIT; unquantized FP16 OpenAI Whisper large-v3-turbo)
- ggml-large-v3-turbo.bin: ggerganov/whisper.cpp @ 98aa99a0 (MIT; unquantized FP16 OpenAI Whisper large-v3-turbo)
- nllb-ct2: JustFrederik/nllb-200-distilled-600M-ct2-int8 @ 302d78f0
  NLLB-200 by Meta AI, licensed CC BY-NC 4.0 (non-commercial use only):
  https://creativecommons.org/licenses/by-nc/4.0/
'@ | Set-Content (Join-Path $notices 'MODELS.txt') -Encoding utf8
Copy-Item (Join-Path $PSScriptRoot 'run.bat') $out

$size = (Get-ChildItem $out -Recurse -File | Measure-Object Length -Sum).Sum
"assembled $out ($([math]::Round($size / 1MB)) MB)"
