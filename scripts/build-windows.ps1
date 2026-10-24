[CmdletBinding()]
param(
    [switch]$UseCurrentPython,
    [string]$InnoSetupCompiler,
    [switch]$PortableArchive
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'La création de Planificateur-SDG-Installation.exe nécessite Windows 10/11 64 bits.'
}
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments, [string]$Failure)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Failure (code $LASTEXITCODE)" }
}

function Find-InnoCompiler {
    if ($InnoSetupCompiler) {
        if (-not (Test-Path -LiteralPath $InnoSetupCompiler -PathType Leaf)) {
            throw "Compilateur Inno Setup introuvable : $InnoSetupCompiler"
        }
        return (Resolve-Path -LiteralPath $InnoSetupCompiler).Path
    }
    $onPath = Get-Command ISCC.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $candidates = @()
    if ($onPath) { $candidates += $onPath.Source }
    if (${env:ProgramFiles(x86)}) { $candidates += (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe') }
    if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe') }
    if ($env:LOCALAPPDATA) { $candidates += (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe') }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw 'Inno Setup 6 est requis. Installez-le depuis https://jrsoftware.org/isdl.php, puis relancez le script (ou utilisez -InnoSetupCompiler chemin\ISCC.exe).'
}

function Assert-NoExistingInstallation {
    # A test using the real stable AppId would replace an existing uninstall
    # registration, even with /DIR pointing at a temporary directory.
    $source = Get-Content -LiteralPath (Join-Path $projectRoot 'installer\GardePlan.iss') -Raw -Encoding UTF8
    $match = [regex]::Match($source, '(?m)^AppId=\{\{([0-9A-Fa-f-]{36})\}\s*$')
    if (-not $match.Success) { throw 'AppId stable introuvable dans installer\GardePlan.iss.' }
    $leaf = '{' + $match.Groups[1].Value + '}_is1'
    $keyPath = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + $leaf
    foreach ($hive in @([Microsoft.Win32.RegistryHive]::CurrentUser, [Microsoft.Win32.RegistryHive]::LocalMachine)) {
        foreach ($view in @([Microsoft.Win32.RegistryView]::Registry32, [Microsoft.Win32.RegistryView]::Registry64)) {
            $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($hive, $view)
            try {
                $key = $base.OpenSubKey($keyPath)
                if ($null -ne $key) {
                    $key.Close()
                    throw "Planificateur — Service de garde est déjà installé sur ce poste. Le contrôle automatique utilise son AppId réel et ne peut pas remplacer votre installation. Exécutez la compilation sur le runner Windows propre de GitHub Actions ou dans une machine Windows de test vierge."
                }
            } finally { $base.Close() }
        }
    }
}

function Test-FrozenApplication {
    param([string]$Executable, [string]$ReportPath, [string]$ExpectedVersion)
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Exécutable absent : $Executable"
    }
    if (Test-Path -LiteralPath $ReportPath) { Remove-Item -LiteralPath $ReportPath -Force }
    Write-Host "Contrôle réel : $Executable"
    # Run from its own directory to catch accidental source imports. A bounded
    # wait also stops a native Qt error dialog from blocking the build forever.
    $process = Start-Process -FilePath $Executable -ArgumentList @('--check-installation', ('"{0}"' -f $ReportPath)) -WorkingDirectory (Split-Path $Executable -Parent) -PassThru
    try {
        if (-not $process.WaitForExit(120000)) {
            try { $process.Kill(); $null = $process.WaitForExit(5000) }
            catch { Write-Warning "Le processus de contrôle n'a pas pu être arrêté : $_" }
            throw "Le contrôle a dépassé deux minutes : $Executable"
        }
        $process.Refresh()
        if ($process.ExitCode -ne 0) { throw "Le contrôle de l'exécutable a échoué (code $($process.ExitCode)). Consultez $ReportPath." }
    } finally { $process.Dispose() }
    if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) { throw "Le contrôle n'a pas produit son fichier JSON : $ReportPath" }
    $report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($report.success -ne $true -or $report.frozen -ne $true -or $report.version -ne $ExpectedVersion) {
        throw "Le contrôle ne confirme pas un exécutable gelé valide de version $ExpectedVersion : $ReportPath"
    }
    if ($report.qt_platform -ne 'windows') { throw "Le module Qt natif Windows n'a pas été chargé : $ReportPath" }
    foreach ($name in @('qt_application', 'coverage_and_exact_minutes', 'sqlite_save_reopen_backup', 'dashboard_day_and_week', 'pdf_export_preview_print_modules', 'ortools_cp_sat_generation', 'offline_operations')) {
        $property = $report.checks.PSObject.Properties[$name]
        if ($null -eq $property -or $property.Value -ne $true) { throw "Contrôle absent ou en échec : $name ($ReportPath)" }
    }
}

function Invoke-SilentUninstall {
    param([string]$Uninstaller)
    $process = Start-Process -FilePath $Uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru
    try {
        if ($process.ExitCode -ne 0) { throw "La désinstallation de contrôle a échoué (code $($process.ExitCode))." }
    } finally { $process.Dispose() }
}

# Fail before downloading dependencies if the installer compiler is unavailable.
$installerDirectory = Join-Path $projectRoot 'dist\installer'
$verificationDirectory = Join-Path $projectRoot 'dist\verification'
New-Item -ItemType Directory -Path $installerDirectory, $verificationDirectory -Force | Out-Null
$installer = Join-Path $installerDirectory 'Planificateur-SDG-Installation.exe'
if (Test-Path -LiteralPath $installer) { Remove-Item -LiteralPath $installer -Force }
foreach ($name in @('portable.json', 'installed.json', 'uninstall.json')) {
    $oldReport = Join-Path $verificationDirectory $name
    if (Test-Path -LiteralPath $oldReport) { Remove-Item -LiteralPath $oldReport -Force }
}

$compiler = Find-InnoCompiler
Assert-NoExistingInstallation

$pythonCheck = "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8, 'Python 3.12 64 bits est requis'"
if ($UseCurrentPython) {
    $bootstrap = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    Invoke-Checked -FilePath $bootstrap -Arguments @('-c', $pythonCheck) -Failure 'Python 3.12 64 bits est requis'
    Invoke-Checked -FilePath $bootstrap -Arguments @('-m', 'venv', '.venv') -Failure "Création de l'environnement Python impossible"
} else {
    Invoke-Checked -FilePath 'py' -Arguments @('-3.12', '-c', $pythonCheck) -Failure 'Python 3.12 64 bits est requis'
    Invoke-Checked -FilePath 'py' -Arguments @('-3.12', '-m', 'venv', '.venv') -Failure "Création de l'environnement Python impossible"
}
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
Invoke-Checked -FilePath $python -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip') -Failure 'Mise à jour de pip impossible'
Invoke-Checked -FilePath $python -Arguments @('-m', 'pip', 'install', '-e', '.[dev]') -Failure 'Installation des bibliothèques impossible'
$version = (& $python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])").Trim()
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^\d+\.\d+\.\d+$') { throw 'La version de pyproject.toml doit contenir trois nombres (exemple : 0.1.0).' }

$previousQtPlatform = [Environment]::GetEnvironmentVariable('QT_QPA_PLATFORM', 'Process')
try {
    $env:QT_QPA_PLATFORM = 'offscreen'
    Invoke-Checked -FilePath $python -Arguments @('-m', 'pytest', '-q') -Failure "Les tests doivent réussir avant la création de l'installateur"
    # Native Windows Qt platform must load in both actual-executable checks.
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    Invoke-Checked -FilePath $python -Arguments @('-m', 'PyInstaller', '--noconfirm', '--clean', 'GardePlan.spec') -Failure "Création de l'exécutable impossible"
    $portable = Join-Path $projectRoot 'dist\GardePlan\Planificateur-SDG.exe'
    Test-FrozenApplication -Executable $portable -ReportPath (Join-Path $verificationDirectory 'portable.json') -ExpectedVersion $version
    Invoke-Checked -FilePath $compiler -Arguments @(("/DAppVersion=$version"), ("/DSourceRoot=$projectRoot"), (Join-Path $projectRoot 'installer\GardePlan.iss')) -Failure "Création de l'installateur impossible"
    if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw "Inno Setup n'a pas créé Planificateur-SDG-Installation.exe." }

    Assert-NoExistingInstallation
    if ($env:RUNNER_TEMP) { $installDirectory = Join-Path $env:RUNNER_TEMP 'GardePlanInstalled' }
    else { $installDirectory = Join-Path ([IO.Path]::GetTempPath()) ('GardePlanInstalled-' + [guid]::NewGuid().ToString('N')) }
    if (Test-Path -LiteralPath $installDirectory) { throw "Le dossier de contrôle doit être vide : $installDirectory" }
    $installedExecutable = Join-Path $installDirectory 'Planificateur-SDG.exe'
    $uninstaller = Join-Path $installDirectory 'unins000.exe'
    # Ask Qt for the same actual data directory used by normal app startup.
    $appData = (& $python -c "from PySide6.QtCore import QCoreApplication,QStandardPaths; a=QCoreApplication([]); a.setOrganizationName('GardePlan'); a.setApplicationName('GardePlan'); print(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))").Trim()
    if ($LASTEXITCODE -ne 0 -or -not $appData) { throw 'Le dossier de données Qt ne peut pas être déterminé.' }
    New-Item -ItemType Directory -Path $appData -Force | Out-Null
    $sentinel = Join-Path $appData ('verification-installation-' + [guid]::NewGuid().ToString('N') + '.txt')
    $token = [guid]::NewGuid().ToString('N')
    [IO.File]::WriteAllText($sentinel, $token, [Text.Encoding]::UTF8)
    try {
        Write-Host 'Installation silencieuse dans un dossier de contrôle temporaire...'
        $process = Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', ('/DIR="{0}"' -f $installDirectory)) -Wait -PassThru
        try {
            if ($process.ExitCode -ne 0) { throw "Installation silencieuse en échec (code $($process.ExitCode))." }
        } finally { $process.Dispose() }
        Test-FrozenApplication -Executable $installedExecutable -ReportPath (Join-Path $verificationDirectory 'installed.json') -ExpectedVersion $version
        if (-not (Test-Path -LiteralPath $uninstaller -PathType Leaf)) { throw 'Le désinstalleur est absent.' }
        Invoke-SilentUninstall -Uninstaller $uninstaller
        if (Test-Path -LiteralPath $installedExecutable) { throw "La désinstallation a conservé l'exécutable installé." }
        if (-not (Test-Path -LiteralPath $sentinel -PathType Leaf) -or [IO.File]::ReadAllText($sentinel) -ne $token) {
            throw "La désinstallation n'a pas conservé le fichier témoin dans le dossier des données."
        }
        [ordered]@{
            success = $true
            version = $version
            installed_executable_removed = $true
            application_data_sentinel_preserved = $true
            checked_at_utc = [DateTime]::UtcNow.ToString('o')
        } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $verificationDirectory 'uninstall.json') -Encoding UTF8
    } finally {
        # Remove only our GUID-named sentinel. Never delete personal databases.
        if (Test-Path -LiteralPath $sentinel) { Remove-Item -LiteralPath $sentinel -Force }
        if (Test-Path -LiteralPath $uninstaller -PathType Leaf) {
            try { Invoke-SilentUninstall -Uninstaller $uninstaller }
            catch { Write-Warning "Le dossier de contrôle nécessite une désinstallation manuelle : $installDirectory. $_" }
        }
    }
    if ($PortableArchive) {
        Compress-Archive -Path (Join-Path $projectRoot 'dist\GardePlan') -DestinationPath (Join-Path $projectRoot 'dist\Planificateur-SDG-Portable.zip') -Force
    }
    Write-Host "Installateur vérifié : $installer"
    Write-Host "Comptes rendus : $verificationDirectory"
} catch {
    # A compiled installer is distributable only after every installed-app test.
    if (Test-Path -LiteralPath $installer) { Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue }
    throw
} finally {
    [Environment]::SetEnvironmentVariable('QT_QPA_PLATFORM', $previousQtPlatform, 'Process')
}
