param(
  [string]$Api  = 'http://127.0.0.1:8011',
  [string]$User = 'store_demo3',
  [string]$Pass = 'Store!123',
  [int]$PartId = 0,
  [switch]$Cleanup = $false
)

$ErrorActionPreference = 'Stop'

# 0) Login (gerekirse)
if (-not $script:__tok -or $script:__tok -eq '') {
  $script:__tok = (Invoke-RestMethod "$Api/auth/login" -Method Post -ContentType 'application/x-www-form-urlencoded' -Body @{
    username=$User; password=$Pass
  }).access_token
}
$hdr = @{ Authorization = "Bearer $script:__tok" }

# 1) PartID seç
# - Eğer -PartId > 0 verildiyse onu kullan
# - Verilmediyse below-min'den seç; orada da yoksa 1'e düş
$PartIdSel = 1
if ($PartId -gt 0) {
  $PartIdSel = [int]$PartId
} else {
  try {
    $bm = Invoke-RestMethod "$Api/parts/below-min?limit=1" -Headers $hdr
    if     ($bm -is [System.Array] -and $bm.Count)                                                   { $PartIdSel = [int]$bm[0].PartID }
    elseif ($bm.PSObject.Properties.Name -contains 'value' -and $bm.value -is [System.Array] -and $bm.value.Count) { $PartIdSel = [int]$bm.value[0].PartID }
  } catch {}
}

# 2) Receive öncesi stok
try { $before = Invoke-RestMethod "$Api/parts/id/$PartIdSel" -Headers $hdr }
catch { throw "Seçilen PartID=$PartIdSel bulunamadı/pasif: $($_.Exception.Message)" }
$stockBefore = [int]$before.CurrentStock

# 3) PO oluştur → place → receive
function New-PO {
  param([int]$SupplierIdParam, [int]$PartIdParam)
  $body = @{ SupplierID=$SupplierIdParam; PartID=$PartIdParam; Qty=1; UnitPrice=10.00 } | ConvertTo-Json
  try { Invoke-RestMethod "$Api/purchase-orders" -Method POST -Headers $hdr -ContentType 'application/json' -Body $body } catch { $null }
}
$po = New-PO -SupplierIdParam 1 -PartIdParam $PartIdSel
if (-not $po) { $po = New-PO -SupplierIdParam 2 -PartIdParam $PartIdSel }
if (-not $po) { throw "PO oluşturulamadı." }
$poid = [int]$po.POID

Invoke-RestMethod "$Api/purchase-orders/$poid/place"   -Method POST -Headers $hdr | Out-Null
Invoke-RestMethod "$Api/purchase-orders/$poid/receive" -Method POST -Headers $hdr | Out-Null

# 4) Stok +1
$after = Invoke-RestMethod "$Api/parts/id/$PartIdSel" -Headers $hdr
$stockAfter = [int]$after.CurrentStock
$delta = $stockAfter - $stockBefore

# 5) EXACT reason ile tek IN
$reason = "PO Receive #$poid"
function Get-Rows([object]$resp){
  $candidates = @($resp.data, $resp.value, $resp.items, $resp)
  $arr = $candidates | Where-Object { $_ -is [System.Array] } | Select-Object -First 1
  if ($null -eq $arr) { @() } else { $arr }
}
$resp = Invoke-RestMethod "$Api/warehouse/txns?reason=$( [uri]::EscapeDataString($reason) )" -Headers $hdr
$rowsExact = (Get-Rows $resp) | Where-Object { $_.TxnType -eq 'IN' -and $_.Reason -eq $reason }
$cntExact = @($rowsExact).Count

# 6) İkinci receive → 409 beklenir
$secondOk409 = $false
try {
  Invoke-RestMethod "$Api/purchase-orders/$poid/receive" -Method POST -Headers $hdr | Out-Null
} catch {
  $code = $null
  if ($_.Exception.Response) { try { $code = $_.Exception.Response.StatusCode.value__ } catch {} }
  if ($code -eq 409) { $secondOk409 = $true }
}

# 7) Özet
Write-Host "POID=$poid | PartID=$PartIdSel | Before=$stockBefore → After=$stockAfter (Δ=$delta) | IN(exact)=$cntExact | 2nd receive 409: $secondOk409" -ForegroundColor Cyan
if ($cntExact -eq 1 -and $delta -eq 1 -and $secondOk409) {
  Write-Host "PASS ✅ — Tek IN + stok +1 + ikinci receive 409 doğrulandı." -ForegroundColor Green
} else {
  Write-Host "FAIL ⚠️ — Beklenen koşullar sağlanmadı. İnceleme gerekli." -ForegroundColor Yellow
}

# 8) (Opsiyonel) Cleanup — stoku geri al
if ($Cleanup) {
  try {
    $outBody = @{ PartID = $PartIdSel; Quantity = 1; Reason = "smoketest revert PO#$poid" } | ConvertTo-Json
    Invoke-RestMethod "$Api/warehouse/out" -Method POST -Headers $hdr -ContentType 'application/json' -Body $outBody | Out-Null
    $afterClean = Invoke-RestMethod "$Api/parts/id/$PartIdSel" -Headers $hdr
    Write-Host "Cleanup yapıldı. Final stock: $([int]$afterClean.CurrentStock)" -ForegroundColor DarkGray
  } catch {
    Write-Host ("Cleanup başarısız: " + $_.Exception.Message) -ForegroundColor Yellow
  }
}
