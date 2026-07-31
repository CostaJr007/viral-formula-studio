# Push local .env secrets to Code Engine app vfs-api.
# Requires: IBM Cloud CLI + code-engine plugin + logged in.
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\push-env-to-code-engine.ps1
# Optional:
#   -ProjectName viral-formula-studio -AppName vfs-api

param(
  [string]$ProjectName = "viral-formula-studio",
  [string]$AppName = "vfs-api",
  [string]$Region = "us-south",
  [string]$EnvFile = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $PSScriptRoot "..\.env"))) {
  $root = Resolve-Path (Join-Path $PSScriptRoot "..")
} else {
  $root = Resolve-Path (Join-Path $PSScriptRoot "..")
}
if (-not $EnvFile) { $EnvFile = Join-Path $root ".env" }

Write-Host "Env file: $EnvFile"
if (-not (Test-Path $EnvFile)) { throw "Missing $EnvFile — create local .env first." }

# Keys we push to production API (never print full values)
$wanted = @(
  "MODEL_PROVIDER",
  "IBM_WATSONX_API_KEY",
  "IBM_WATSONX_PROJECT_ID",
  "IBM_WATSONX_URL",
  "WATSONX_MODEL_ID",
  "WATSONX_FALLBACK_MODEL_ID",
  "WATSONX_VISION_MODEL_ID",
  "GROQ_API_KEY",
  "GROQ_LLM_MODEL_ID",
  "GROQ_LLM_FALLBACK",
  "OPENAI_API_KEY",
  "OPENAI_MODEL_ID",
  "OPENAI_FALLBACK",
  "TAVILY_API_KEY"
)

$kv = @{}
Get-Content $EnvFile | ForEach-Object {
  $line = $_.Trim()
  if (-not $line -or $line.StartsWith("#")) { return }
  $i = $line.IndexOf("=")
  if ($i -lt 1) { return }
  $k = $line.Substring(0, $i).Trim()
  $v = $line.Substring($i + 1).Trim().Trim('"').Trim("'")
  if ($wanted -contains $k -and $v) { $kv[$k] = $v }
}

if (-not $kv.ContainsKey("GROQ_API_KEY")) { throw "GROQ_API_KEY missing in .env" }
if (-not $kv.ContainsKey("IBM_WATSONX_API_KEY")) { throw "IBM_WATSONX_API_KEY missing in .env" }

Write-Host "Will set $($kv.Count) env vars on $AppName (values hidden):"
$kv.Keys | Sort-Object | ForEach-Object {
  $v = $kv[$_]
  $tail = if ($v.Length -gt 4) { $v.Substring($v.Length - 4) } else { "****" }
  Write-Host ("  {0}=...{1}" -f $_, $tail)
}

$ibm = Get-Command ibmcloud -ErrorAction SilentlyContinue
if (-not $ibm) {
  Write-Host ""
  Write-Host "IBM Cloud CLI not installed — cannot push automatically from this machine."
  Write-Host "Install: https://cloud.ibm.com/docs/cli"
  Write-Host "Then: ibmcloud login --sso   OR   ibmcloud login --apikey <KEY>"
  Write-Host "      ibmcloud plugin install code-engine"
  Write-Host "      ibmcloud target -r $Region"
  Write-Host "      ibmcloud ce project select -n $ProjectName"
  Write-Host "      re-run this script"
  Write-Host ""
  Write-Host "OR paste manually in console (Application $AppName → Environment variables):"
  Write-Host "--------------------------------------------------"
  $kv.GetEnumerator() | Sort-Object Name | ForEach-Object {
    Write-Host ("{0}={1}" -f $_.Key, $_.Value)
  }
  Write-Host "--------------------------------------------------"
  exit 2
}

Write-Host "Selecting Code Engine project $ProjectName ..."
ibmcloud target -r $Region | Out-Host
ibmcloud ce project select -n $ProjectName | Out-Host

# Build env-from-literal args
$envArgs = @()
foreach ($k in ($kv.Keys | Sort-Object)) {
  $envArgs += "--env"
  $envArgs += ("{0}={1}" -f $k, $kv[$k])
}

Write-Host "Updating application $AppName (new revision)..."
& ibmcloud ce app update --name $AppName @envArgs
if ($LASTEXITCODE -ne 0) { throw "ibmcloud ce app update failed with $LASTEXITCODE" }

Write-Host "Done. Wait ~30–60s for revision, then:"
Write-Host "  curl -s https://vfs-api.2cfhg08pznl4.us-south.codeengine.appdomain.cloud/api/health"
