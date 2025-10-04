param(
  [string]$Base       = "http://127.0.0.1:8011",
  [string]$Username   = "store1",
  [string]$Password   = "Passw0rd!",
  [int]   $SupplierID = 1,
  [int]   $PartID     = 1,
  [int]   $Qty        = 3,
  [double]$UnitPrice  = 10
)

$ErrorActionPreference = "Stop"
$Base = $Base.Trim().TrimEnd('/')

function LoginOrRegister($Base,$Username,$Password) {
  try {
    $form = @{ username=$Username; password=$Password }
    $t = Invoke-RestMethod "$Base/auth/login" -Method POST -ContentType 'application/x-www-form-urlencoded' -Body $form -TimeoutSec 10
    if ($t.access_token) { return @{ Authorization="Bearer $($t.access_token)" } }
  } catch {}

  try {
    $body = @{ username=$Username; password=$Password; full_name="Store User"; role="store" } | ConvertTo-Json
    $null = Invoke-RestMethod "$Base/auth/register" -Method POST -ContentType 'application/json' -Body $body -TimeoutSec 10
  } catch {}

  $form = @{ username=$Username; password=$Password }
  $t = Invoke-RestMethod "$Base/auth/login" -Method POST -ContentType 'application/x-www-form-urlencoded' -Body $form -TimeoutSec 10
  if (-not $t.access_token) { throw "Token alınamadı." }
  return @{ Authorization="Bearer $($t.access_token)" }
}

function GET($url, $hdr=$null) {
  if ($hdr) { return Invoke-RestMethod -Uri $url -Headers $hdr -TimeoutSec 10 }
  else      { return Invoke-RestMethod -Uri $url -TimeoutSec 10 }
}

function POSTJSON($url, $bodyObj=$null, $hdr=$null) {
  $params = @{ Uri=$url; Method="POST"; TimeoutSec=20 }
  if ($hdr) { $params.Headers = $hdr }
  if ($bodyObj -ne $null) { $params.ContentType='application/json'; $params.Body=($bodyObj|ConvertTo-Json) }
  return Invoke-RestMethod @params
}

# 0) Health
GET "$Base/health" | Out-Null
GET "$Base/db-ping" | Out-Null

# 1) Auth
$hdr = LoginOrRegister $Base $Username $Password

# 2) Create → Place → Receive
$po = POSTJSON "$Base/purchase-orders" @{ SupplierID=$SupplierID; PartID=$PartID; Qty=$Qty; UnitPrice=$UnitPrice } $hdr
$po | ConvertTo-Json -Depth 6 | Out-Host
POSTJSON ("$Base/purchase-orders/{0}/place"   -f $po.POID) $null $hdr | Out-Host
POSTJSON ("$Base/purchase-orders/{0}/receive" -f $po.POID) $null $hdr | Out-Host

# 3) Kısa özet
(GET "$Base/warehouse/txns" $hdr) | Select-Object -First 5 | ConvertTo-Json -Depth 4 | Out-Host
Write-Host "smoke tamamlandı." -ForegroundColor Cyan
