# Whisper の照合用の音声を Windows の音声合成 (SAPI) で作る。
#
#     powershell -File native/reference/make_audio_corpus.ps1   ->  native/testdata/whisper/audio/*.wav
#
# 文は corpus/sentences.tsv の英語と日本語。16 kHz / 16 bit / モノラル。声は PC によって違うので、
# 作り直したら export_whisper.py で基準も作り直す (できた音声はリポジトリに置く)。
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'testdata/whisper/audio'
New-Item -ItemType Directory -Force $out | Out-Null
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$voices = @{
    'English'  = @('Microsoft Zira Desktop')
    'Japanese' = @('Microsoft Haruka Desktop')
}
# System.Speech から選べるのは Desktop の声だけなので、話す速さを変えて幅を出す
$prefix = @{ 'English' = 'en'; 'Japanese' = 'ja' }
$count = @{ 'English' = 0; 'Japanese' = 0 }
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
foreach ($line in Get-Content -Encoding UTF8 (Join-Path $PSScriptRoot 'corpus/sentences.tsv')) {
    if ($line.StartsWith('#') -or -not $line) { continue }
    $language, $text = $line -split "`t", 2
    if (-not $voices.ContainsKey($language)) { continue }
    $i = $count[$language]++
    $list = $voices[$language]
    $synth.SelectVoice($list[$i % $list.Count])
    $synth.Rate = @(0, -3, 3)[$i % 3]
    $path = Join-Path $out ('{0}{1:d2}.wav' -f $prefix[$language], $i)
    $synth.SetOutputToWaveFile($path, $format)
    $synth.Speak($text)
    $synth.SetOutputToNull()
}
$synth.Dispose()
Get-ChildItem $out | Measure-Object -Property Length -Sum | ForEach-Object { "{0} files, {1:n0} bytes" -f $_.Count, $_.Sum }
