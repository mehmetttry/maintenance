# backend/tests/local-smoke.ps1
<#
 Amaç:
 - Lokal ortamda CI akışını taklit ederek "PO Receive" smoke testini çalıştırır.
 Kullanım:
   powershell.exe -ExecutionPolicy Bypass -File ".\backend\tests\local-smoke.ps1" -PartId 1 -Port 8011 -DoSeed
#>

[CmdletBinding()]
param(
  [int]$PartId = 1,
  [string]$ApiHost = "127.0.0.1",
  [int]$Port = 8011,
  [switch]$DoSeed,
  [string]$DatabaseUrl = "sqlite:///./test.db"
)

$ErrorActionPreference = 'Stop'

function Write-Section([string]$msg) { Write-Host "=== $msg ===" }

function Resolve-Python {
  if ($env:VIRTUAL_ENV) {
    $p = Join-Path $env:VIRTUAL_ENV "Scripts/python.exe"
    if (Test-Path $p) { return $p }
  }
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return "$($py.Source)" }
  throw "Python yürütücüsü bulunamadı. Lütfen Python'ı PATH'e ekleyin."
}

$PythonExe = Resolve-Python
Write-Section "Python: $PythonExe"

# 1) Paketler
Write-Section "Python paketleri kuruluyor"
& $PythonExe -m pip install --upgrade pip
if (Test-Path "backend/requirements.txt") {
  & $PythonExe -m pip install -r "backend/requirements.txt"
} else {
  Write-Host "requirements.txt yok, temel paketler kuruluyor"
  & $PythonExe -m pip install fastapi uvicorn "pydantic>=2" sqlalchemy httpx
}

# 2) Ortam değişkenleri
Write-Section "Ortam değişkenleri ayarlanıyor"
$env:DATABASE_URL = $DatabaseUrl

# 3) (Opsiyonel) Seed — global 'app' paketi çakışmasını aşmak için runpy + PYTHONPATH
$BackendDir = "backend"
$SeedRel    = "scripts/seed_demo.py"
$SeedPath   = Join-Path $BackendDir $SeedRel
if ($DoSeed -and (Test-Path $SeedPath)) {
  Write-Section "Seed scripti çalıştırılıyor (store_demo3 / Store!123)"
  $env:PYTHONPATH = (Resolve-Path $BackendDir).Path
  $seedCmd = 'import os,runpy; os.chdir("'+$BackendDir+'"); os.environ["PYTHONPATH"]=os.getcwd(); runpy.run_path("scripts/seed_demo.py", run_name="__main__")'
  $seedProc = Start-Process -FilePath $PythonExe -ArgumentList "-c", $seedCmd -WorkingDirectory $BackendDir -PassThru -NoNewWindow -Wait
  if ($seedProc.ExitCode -ne 0) {
    Write-Host "Uyarı: seed scripti hata ile döndü (ExitCode=$($seedProc.ExitCode)). Devam ediliyor..."
  }
} elseif ($DoSeed) {
  Write-Host "Uyarı: $SeedPath bulunamadı, seed atlandı"
}

# 4) API (uvicorn) başlat — backend çalışma dizininde
Write-Section "Uvicorn başlatılıyor"
$apiArgs = "-m uvicorn app.main:app --host $ApiHost --port $Port"
$proc = Start-Process -FilePath $PythonExe -ArgumentList $apiArgs -WorkingDirectory $BackendDir -PassThru
Write-Host "Uvicorn PID: $($proc.Id)"

try {
  # 5) Health-check
  Write-Section "Health-check bekleniyor"
  $healthUrl = "http://$ApiHost`:$Port/health"
  $ok = $false
  for ($i=0; $i -lt 60; $i++) {
    try {
      $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
      if ($resp.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Seconds 1 }
  }
  if (-not $ok) { throw "API health endpoint hazır değil: $healthUrl" }
  Write-Host "API hazır: $healthUrl"

  # 6) Smoketest — **call operator (&)** ile çalıştır
  Write-Section "PO Receive smoketest çalıştırılıyor"
  $smoke = "backend/tests/po-receive-smoketest.ps1"
  if (-not (Test-Path $smoke)) { throw "Smoketest script bulunamadı: $smoke" }

  & $smoke -PartId $PartId -Cleanup -CI

  Write-Section "Smoke test BAŞARILI"
  exit 0
}
catch {
  Write-Host "HATA: $($_.Exception.Message)"
  exit 1
}
finally {
  if ($proc -and -not $proc.HasExited) {
    Write-Section "Uvicorn sonlandırılıyor"
    Stop-Process -Id $proc.Id -Force
  }
}
