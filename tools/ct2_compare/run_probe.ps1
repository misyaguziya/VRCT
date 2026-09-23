param(
    [Parameter(Mandatory = $true)]
    [string]$Python,
    [Parameter(Mandatory = $true)]
    [string]$Model,
    [int]$TimeoutSeconds = 180,
    [switch]$SkipInference
)

$arguments = @(
    'tools\ct2_compare\destroy_probe.py',
    $Model,
    '--device', 'cpu',
    '--compute-type', 'float32'
)
if ($SkipInference) {
    $arguments += '--skip-inference'
}

$outputPath = Join-Path ([IO.Path]::GetTempPath()) ("ct2-probe-" + [guid]::NewGuid() + ".out")
$errorPath = Join-Path ([IO.Path]::GetTempPath()) ("ct2-probe-" + [guid]::NewGuid() + ".err")
$argumentString = ($arguments | ForEach-Object {
    if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
}) -join ' '
$process = Start-Process -FilePath (Resolve-Path $Python).Path `
    -ArgumentList $argumentString `
    -WorkingDirectory (Get-Location).Path `
    -RedirectStandardOutput $outputPath `
    -RedirectStandardError $errorPath `
    -PassThru
if ($process.WaitForExit($TimeoutSeconds * 1000)) {
    Get-Content $outputPath -Raw
    $stderr = Get-Content $errorPath -Raw
    if ($stderr) {
        Write-Output "STDERR: $stderr"
    }
    Write-Output "exit=$($process.ExitCode)"
    exit $process.ExitCode
}

Get-Content $outputPath -Raw
Write-Output "TIMEOUT=${TimeoutSeconds}s"
try {
    Stop-Process -Id $process.Id -Force -ErrorAction Stop
} catch {
    Write-Output "kill_error=$($_.Exception.Message)"
}
if (!$process.HasExited) {
    Write-Output 'kill_incomplete=1'
}
Get-Content $errorPath -Raw
Remove-Item $outputPath, $errorPath -Force -ErrorAction SilentlyContinue
Write-Output 'killed=1'
exit 124
