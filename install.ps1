# PayU CLI installer for Windows
# Usage: irm https://raw.githubusercontent.com/payu-intrepos/payu-cli/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$repo = "payu-intrepos/payu-cli"
$zipName = "payu_windows_x86_64.zip"
$installDir = "$env:LOCALAPPDATA\payu-cli"
$url = "https://github.com/$repo/releases/latest/download/$zipName"

Write-Host "Downloading PayU CLI..." -ForegroundColor Cyan
$tmp = New-TemporaryFile | Rename-Item -NewName { $_.Name + ".zip" } -PassThru
Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing

Write-Host "Extracting..."
if (Test-Path $installDir) { Remove-Item $installDir -Recurse -Force }
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Expand-Archive -Path $tmp -DestinationPath $installDir -Force
Remove-Item $tmp -Force

# Add to user PATH if not already there
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$installDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$installDir;$userPath", "User")
    Write-Host ""
    Write-Host "Added $installDir to your PATH." -ForegroundColor Yellow
    Write-Host "Restart your terminal for the change to take effect." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "PayU CLI installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Get started:"
Write-Host "  payu version           # verify installation"
Write-Host "  payu config set        # configure credentials"
Write-Host "  payu --help            # see all commands"
