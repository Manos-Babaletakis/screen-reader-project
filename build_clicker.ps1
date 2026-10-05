# Builds, signs and installs the uiAccess mouse helper (see clicker.py).
# Run from an ADMINISTRATOR PowerShell:   powershell -ExecutionPolicy Bypass -File build_clicker.ps1
#
# Windows only grants uiAccess to an .exe that (1) asks for it in its manifest, (2) is signed
# by a certificate this PC trusts and (3) is installed in a protected folder (Program Files).
# A fresh self-signed certificate is made for each build. Its private key is deleted right
# after signing, so nothing else can ever be signed with it. Certificates from earlier builds
# are removed from the trusted stores.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$subject = "CN=OkeyClicker local code signing"
$dest = Join-Path $env:ProgramFiles "OkeyClicker"

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this from an administrator PowerShell."
}

# 1. build (onedir: a onefile build runs the real program as a child process without uiAccess)
python -m PyInstaller --noconfirm --clean --onedir --console --uac-uiaccess --name clicker `
    --distpath build/clicker-dist --workpath build/clicker-work --specpath build clicker.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
$exe = Resolve-Path "build/clicker-dist/clicker/clicker.exe"

# 2. remove certificates from earlier builds
#    (-DeleteKey only exists with an explicit Cert:\ path in Windows PowerShell 5.1, not when piping)
foreach ($store in "Cert:\LocalMachine\Root", "Cert:\LocalMachine\TrustedPublisher", "Cert:\CurrentUser\My") {
    foreach ($old in @(Get-ChildItem $store | Where-Object { $_.Subject -eq $subject })) {
        $path = Join-Path $store $old.Thumbprint
        if ($old.HasPrivateKey) { Remove-Item -Path $path -DeleteKey } else { Remove-Item -Path $path }
    }
}

# 3. new certificate, trusted on this PC
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject `
    -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddYears(10)
$cer = Join-Path $env:TEMP "okeyclicker.cer"
Export-Certificate -Cert $cert -FilePath $cer | Out-Null
Import-Certificate -FilePath $cer -CertStoreLocation Cert:\LocalMachine\Root | Out-Null
Import-Certificate -FilePath $cer -CertStoreLocation Cert:\LocalMachine\TrustedPublisher | Out-Null
Remove-Item $cer

# 4. sign, then destroy the private key
$sig = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -HashAlgorithm SHA256
Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -DeleteKey
if ($sig.Status -ne "Valid") { throw "Signing failed: $($sig.StatusMessage)" }

# 5. install into Program Files
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Copy-Item (Split-Path $exe) $dest -Recurse
$check = Get-AuthenticodeSignature (Join-Path $dest "clicker.exe")
Write-Host "Installed $dest\clicker.exe - signature: $($check.Status)"
