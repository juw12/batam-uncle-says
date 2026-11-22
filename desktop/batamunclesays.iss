; BatamUncleSays for Windows - per-user installer (no admin rights). build.py compiles it with:
;   iscc /DAppVersion=1.0.0 /DSourceDir=<dist\BatamUncleSays> /DOutputDir=<dist> /DIconFile=<build\batamunclesays.ico> batamunclesays.iss
; Installs to %LOCALAPPDATA%\Programs\BatamUncleSays, adds BatamUncleSays to the Start menu (and optionally the desktop) and lists it
; in Settings > Apps. The window keeps its data (what you saved in it) in %LOCALAPPDATA%\BatamUncleSays, which
; uninstalling leaves in place so a reinstall finds it again.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "dist\BatamUncleSays"
#endif
#ifndef OutputDir
  #define OutputDir "dist"
#endif
#ifndef IconFile
  #define IconFile "build\batamunclesays.ico"
#endif

[Setup]
AppId={{E81247BA-698B-569E-A6DE-E1E1C366EEFB}
AppName=BatamUncleSays
AppVersion={#AppVersion}
AppVerName=BatamUncleSays {#AppVersion}
AppPublisher=Juwen Lie
AppPublisherURL=https://juw12.github.io/batam-uncle-says/
AppSupportURL=https://github.com/juw12/batam-uncle-says
DefaultDirName={autopf}\BatamUncleSays
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=BatamUncleSays-Windows-Setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\BatamUncleSays.exe
UninstallDisplayName=BatamUncleSays
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\BatamUncleSays"; Filename: "{app}\BatamUncleSays.exe"; Comment: "Batam day trips planned around your ferry"
Name: "{userdesktop}\BatamUncleSays"; Filename: "{app}\BatamUncleSays.exe"; Comment: "Batam day trips planned around your ferry"; Tasks: desktopicon

[Run]
Filename: "{app}\BatamUncleSays.exe"; Description: "{cm:LaunchProgram,BatamUncleSays}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\BatamUncleSays.exe"; Parameters: "--stop"; Flags: runhidden waituntilterminated; RunOnceId: "StopBatamUncleSays"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  { Updating: close an open BatamUncleSays window first so its files can be replaced. }
  if FileExists(ExpandConstant('{app}\BatamUncleSays.exe')) then
    Exec(ExpandConstant('{app}\BatamUncleSays.exe'), '--stop', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;
