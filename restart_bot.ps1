# restart_bot.ps1 -- safe restart of the "Ostrove" production bot.
#
# Steps:
#   1) PRE-FLIGHT: verify the code imports. If not, DO NOT touch the running
#      bot (an old working version beats a crashed new one).
#   2) Stop ALL running bot.py instances (there should be 0 or 1).
#   3) Start exactly one new instance in the background, logs to file.
#   4) Verify exactly one instance is up and the log shows no conflict.
#
# Manual run:  powershell -ExecutionPolicy Bypass -File restart_bot.ps1
# ASCII-only on purpose so it parses regardless of console code page.

$ErrorActionPreference = 'Stop'
$proj = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $proj

# Interpreter: same one prod uses, else fall back to system python.
$py = 'C:\Python313\python.exe'
if (-not (Test-Path $py)) { $py = (Get-Command python).Source }

function Get-BotProcesses {
    Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -match 'bot\.py' }
}

# 1) PRE-FLIGHT -------------------------------------------------------------
Write-Output '[1/4] Pre-flight: checking that code imports...'
& $py -c "import handlers, keyboards, models; handlers.setup_routers()"
if ($LASTEXITCODE -ne 0) {
    Write-Output 'PRE-FLIGHT FAILED: code does not import. Restart aborted, old bot keeps running.'
    exit 1
}
Write-Output '      OK -- code imports.'

# 2) STOP -------------------------------------------------------------------
Write-Output '[2/4] Stopping running bot.py instances...'
$old = Get-BotProcesses
foreach ($p in $old) {
    Write-Output "      stop PID $($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
# Wait for processes to actually exit (so Telegram frees getUpdates).
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Milliseconds 500
    if (-not (Get-BotProcesses)) { break }
}
if (Get-BotProcesses) { Write-Output 'WARNING: some old processes did not exit.' }

# 3) START ------------------------------------------------------------------
Write-Output '[3/4] Starting a fresh instance...'
$errLog = Join-Path $proj 'bot.err.log'
$outLog = Join-Path $proj 'bot.out.log'
# Keep previous error log with a timestamp so history is not lost.
if (Test-Path $errLog) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    Move-Item $errLog (Join-Path $proj "bot.err.$stamp.log") -Force
}
Start-Process -FilePath $py -ArgumentList 'bot.py' -WorkingDirectory $proj `
    -RedirectStandardError $errLog -RedirectStandardOutput $outLog -WindowStyle Hidden

# 4) VERIFY -----------------------------------------------------------------
Write-Output '[4/4] Verifying the bot came up...'
Start-Sleep -Seconds 6
$running = Get-BotProcesses
$count = ($running | Measure-Object).Count
Write-Output "      bot.py instances running: $count"

$problem = $false
if ($count -ne 1) { Write-Output 'WARNING: expected exactly 1 instance!'; $problem = $true }
if (Test-Path $errLog) {
    $tail = Get-Content $errLog -Tail 30 -ErrorAction SilentlyContinue
    if ($tail -match 'TelegramConflictError') {
        Write-Output 'WARNING: TelegramConflictError in log -- a second copy may be running.'; $problem = $true
    }
    if ($tail -match 'Traceback') {
        Write-Output 'WARNING: traceback at startup -- check bot.err.log.'; $problem = $true
    }
}
if ($problem) { exit 2 }
Write-Output 'Restart OK. New code is live.'
