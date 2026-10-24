; Compile through scripts/build-windows.ps1. Version comes from pyproject.toml.
#ifndef AppVersion
  #error AppVersion is required (use scripts/build-windows.ps1).
#endif
#ifndef SourceRoot
  #error SourceRoot is required (use scripts/build-windows.ps1).
#endif

[Setup]
AppId={{C22BDB76-F678-4E44-9BD7-7305A60E5B52}
AppName=Planificateur — Service de garde
AppVersion={#AppVersion}
AppPublisher=Planificateur — Service de garde
AppVerName=Planificateur — Service de garde {#AppVersion}
VersionInfoVersion={#AppVersion}.0
DefaultDirName={localappdata}\Programs\GardePlan
DefaultGroupName=Planificateur — Service de garde
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.17763
UsePreviousAppDir=yes
UsePreviousTasks=yes
UninstallDisplayIcon={app}\Planificateur-SDG.exe
OutputDir={#SourceRoot}\dist\installer
OutputBaseFilename=Planificateur-SDG-Installation
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "francais"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"

[Files]
Source: "{#SourceRoot}\dist\GardePlan\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\Planificateur — Service de garde"; Filename: "{app}\Planificateur-SDG.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Planificateur — Service de garde"; Filename: "{app}\Planificateur-SDG.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Planificateur-SDG.exe"; Description: "Ouvrir Planificateur — Service de garde"; Flags: nowait postinstall skipifsilent

; Deliberately no [UninstallDelete]: personal databases, backups, and history
; live in Qt's AppLocalDataLocation, outside the program installation directory.
