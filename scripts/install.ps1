$ErrorActionPreference = 'Stop'

$projectName = if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { 'pet-exam' }
$envFile = '.env.docker'
$envExample = '.env.docker.example'
$composeEnvFile = '.env'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw 'docker is not installed. Please install Docker Desktop first.'
}

if (-not (Test-Path $envFile)) {
  if (-not (Test-Path $envExample)) {
    throw "Missing $envExample"
  }
  Copy-Item $envExample $envFile
  Write-Host "Created $envFile from $envExample"
}

if (-not (Test-Path 'backend/db.sqlite3')) {
  New-Item -ItemType File -Path 'backend/db.sqlite3' -Force | Out-Null
}

if (Test-Path 'backend/db.sqlite3' -PathType Container) {
  throw 'backend/db.sqlite3 is a directory. Remove it and create a file before deploy.'
}

$composeVersion = docker compose version 2>$null
if (-not $composeVersion) {
  throw 'docker compose plugin is not installed.'
}

$envMap = @{}
Get-Content $envFile | ForEach-Object {
  $line = $_.Trim()
  if (-not $line -or $line.StartsWith('#')) { return }
  $parts = $line.Split('=', 2)
  if ($parts.Count -eq 2) {
    $envMap[$parts[0].Trim()] = $parts[1].Trim()
  }
}

$appBindIp = if ($envMap.ContainsKey('APP_BIND_IP') -and $envMap['APP_BIND_IP']) { $envMap['APP_BIND_IP'] } else { '127.0.0.1' }
$appPort = if ($envMap.ContainsKey('APP_PORT') -and $envMap['APP_PORT']) { $envMap['APP_PORT'] } else { '18080' }

$composeEnvLines = @(
  "APP_BIND_IP=$appBindIp"
  "APP_PORT=$appPort"
)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines((Join-Path (Get-Location) $composeEnvFile), $composeEnvLines, $utf8NoBom)

Write-Host "Starting containers (project: $projectName)..."
docker compose --env-file $envFile -p $projectName up -d --build

Write-Host 'Done.'
Write-Host "Application: http://${appBindIp}:${appPort}"
Write-Host "Admin: http://${appBindIp}:${appPort}/admin/"
