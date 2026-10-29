[CmdletBinding()]
param(
    [switch]$UseCurrentPython,
    [string]$InnoSetupCompiler,
    [switch]$BuildInstaller
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'La création du logiciel portable Windows nécessite Windows 10/11 64 bits.'
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
    param([string]$Executable, [string]$ReportPath, [string]$ExpectedVersion, [bool]$ExpectedPortable = $false, [string]$UpdateArchive = '')
    try {
    if (Test-Path -LiteralPath $ReportPath) { Remove-Item -LiteralPath $ReportPath -Force }
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Exécutable absent : $Executable"
    }
    Write-Host "Contrôle réel : $Executable"
    # Run from its own directory to catch accidental source imports. A bounded
    # wait also stops a native Qt error dialog from blocking the build forever.
    $checkArguments = @('--check-installation', ('"{0}"' -f $ReportPath))
    if ($UpdateArchive) { $checkArguments += @('--check-update-archive', ('"{0}"' -f $UpdateArchive)) }
    $process = Start-Process -FilePath $Executable -ArgumentList $checkArguments -WorkingDirectory (Split-Path $Executable -Parent) -PassThru
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
    if ($report.portable_mode -ne $ExpectedPortable) { throw "Le mode de données du logiciel ne correspond pas au paquet testé : $ReportPath" }
    if ($ExpectedPortable) {
        $property = $report.checks.PSObject.Properties['portable_data_write']
        if ($null -eq $property -or $property.Value -ne $true) { throw "L'écriture des données à côté du logiciel portable n'a pas été confirmée : $ReportPath" }
    }
    foreach ($name in @('qt_application', 'coverage_and_exact_minutes', 'sqlite_save_reopen_backup', 'dashboard_day', 'pdf_export_preview_print_modules', 'ortools_cp_sat_generation', 'offline_operations')) {
        $property = $report.checks.PSObject.Properties[$name]
        if ($null -eq $property -or $property.Value -ne $true) { throw "Contrôle absent ou en échec : $name ($ReportPath)" }
    }
    } catch {
        # Test fixtures only: print the diagnostic before failing the CI job.
        if (Test-Path -LiteralPath $ReportPath -PathType Leaf) {
            try { Write-Host (Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8) }
            catch { Write-Warning "Le rapport de contrôle ne peut pas être lu : $ReportPath" }
        }
        throw
    }
}

function Invoke-SilentUninstall {
    param([string]$Uninstaller)
    $process = Start-Process -FilePath $Uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru
    try {
        if ($process.ExitCode -ne 0) { throw "La désinstallation de contrôle a échoué (code $($process.ExitCode))." }
    } finally { $process.Dispose() }
}

# Portable delivery is the default: no installer compiler or system installation.
$installerDirectory = Join-Path $projectRoot 'dist\installer'
$verificationDirectory = Join-Path $projectRoot 'dist\verification'
$archive = Join-Path $projectRoot 'dist\Planificateur-SDG-Portable.zip'
$stage = Join-Path $projectRoot 'dist\portable\Planificateur-SDG'
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
New-Item -ItemType Directory -Path $installerDirectory, $verificationDirectory -Force | Out-Null
$installer = Join-Path $installerDirectory 'Planificateur-SDG-Installation.exe'
if (Test-Path -LiteralPath $installer) { Remove-Item -LiteralPath $installer -Force }
foreach ($name in @('bundle.json', 'portable.json', 'portable-archive.json', 'installed.json', 'uninstall.json')) {
    $oldReport = Join-Path $verificationDirectory $name
    if (Test-Path -LiteralPath $oldReport) { Remove-Item -LiteralPath $oldReport -Force }
}

$compiler = $null
if ($BuildInstaller) {
    $compiler = Find-InnoCompiler
    Assert-NoExistingInstallation
}

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
    Invoke-Checked -FilePath $python -Arguments @('-m', 'pytest', '-q') -Failure "Les tests doivent réussir avant la création du logiciel portable"
    # Native Windows Qt platform must load in both actual-executable checks.
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    Invoke-Checked -FilePath $python -Arguments @('-m', 'PyInstaller', '--noconfirm', '--clean', 'GardePlan.spec') -Failure "Création de l'exécutable impossible"
    $bundle = Join-Path $projectRoot 'dist\GardePlan'
    Test-FrozenApplication -Executable (Join-Path $bundle 'Planificateur-SDG.exe') -ReportPath (Join-Path $verificationDirectory 'bundle.json') -ExpectedVersion $version
    $stageData = Join-Path $stage 'donnees'
    if (Test-Path -LiteralPath $stageData) {
        if (Get-ChildItem -LiteralPath $stageData -Force | Select-Object -First 1) {
            throw "Le dossier de fabrication contient déjà des données. Conservez ou déplacez le dossier $stage avant une nouvelle compilation."
        }
    }
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
    New-Item -ItemType Directory -Path (Split-Path $stage -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $bundle -Destination $stage -Recurse -Force
    New-Item -ItemType Directory -Path $stageData -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $stage 'portable.mode'), "portable`n", [Text.Encoding]::UTF8)
    @'
PLANIFICATEUR - SERVICE DE GARDE : VERSION PORTABLE

1. Extraire tout le dossier Planificateur-SDG dans un dossier ou une cle USB ou vous pouvez ecrire.
2. Ouvrir Planificateur-SDG.exe depuis ce dossier. Aucune installation.
3. Vos horaires sont conserves dans le sous-dossier donnees. Conserver le dossier complet.

Ne pas lancer depuis le ZIP. Depuis 0.4.0 ou avant : fermer, sauvegarder puis transferer le sous-dossier donnees.
Depuis 0.5.0 : Dossier > Mettre a jour depuis un ZIP prepare la version suivante a cote de l'ancienne.
Garder les deux dossiers pour permettre le retour aux donnees d'avant mise a jour.
'@ | Set-Content -LiteralPath (Join-Path $stage 'LIRE-MOI.txt') -Encoding UTF8
    Invoke-Checked -FilePath $python -Arguments @('-m', 'gardeplan.portable_package', 'manifest', $stage, $version) -Failure 'Inventaire portable impossible'
    Test-FrozenApplication -Executable (Join-Path $stage 'Planificateur-SDG.exe') -ReportPath (Join-Path $verificationDirectory 'portable.json') -ExpectedVersion $version -ExpectedPortable $true
    if (Get-ChildItem -LiteralPath $stageData -Force | Select-Object -First 1) {
        throw 'Le contrôle portable doit nettoyer ses données de test avant de créer le ZIP.'
    }
    Invoke-Checked -FilePath $python -Arguments @('-m', 'gardeplan.portable_package', 'archive', $stage, $archive) -Failure 'Archive portable impossible'
    $extraction = Join-Path ([IO.Path]::GetTempPath()) ('PlanificateurArchive-' + [guid]::NewGuid().ToString('N'))
    try {
        Expand-Archive -LiteralPath $archive -DestinationPath $extraction -Force
        $extractedExecutable = Join-Path $extraction 'Planificateur-SDG\Planificateur-SDG.exe'
        Test-FrozenApplication -Executable $extractedExecutable -ReportPath (Join-Path $verificationDirectory 'portable-archive.json') -ExpectedVersion $version -ExpectedPortable $true -UpdateArchive $archive
    } finally {
        if (Test-Path -LiteralPath $extraction) { Remove-Item -LiteralPath $extraction -Recurse -Force }
    }

    if ($BuildInstaller) {
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
        Write-Host "Installateur facultatif vérifié : $installer"
    }
    Write-Host "Logiciel portable vérifié, sans installation : $archive"
    Write-Host "Comptes rendus : $verificationDirectory"
} catch {
    # Deliver only an archive whose real extracted executable passed validation.
    if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $installer) { Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue }
    throw
} finally {
    [Environment]::SetEnvironmentVariable('QT_QPA_PLATFORM', $previousQtPlatform, 'Process')
}
