#ifndef BundleDir
  #error BundleDir must point to the checked Flutter Release folder
#endif
#ifndef CrtDir
  #error CrtDir must point to the licensed Visual Studio x64 redistributable CRT folder
#endif
#ifndef CompilerLicense
  #error CompilerLicense must point to Inno Setup license.txt
#endif
#ifndef OutputDir
  #define OutputDir "..\build\installer"
#endif

[Setup]
AppId={{8C870A93-47D8-46C4-B4A2-BD776D317CCC}
AppName=RegionCompositor
AppVersion=0.2.0 Preview 2
AppVerName=RegionCompositor 0.2.0 Preview 2
AppPublisher=noobcoderbkr
AppPublisherURL=https://github.com/noobcoderbkr/Diffusion-sprit-clean
AppSupportURL=https://github.com/noobcoderbkr/Diffusion-sprit-clean/issues
DefaultDirName={localappdata}\Programs\RegionCompositor
DefaultGroupName=RegionCompositor
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#OutputDir}
OutputBaseFilename=RegionCompositor-Setup-v0.2.0-flutter.2-x64
SetupIconFile=..\flutter_app\windows\runner\resources\app_icon.ico
UninstallDisplayIcon={app}\region_compositor.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=0.2.0.2

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#CrtDir}\*.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#CompilerLicense}"; DestDir: "{app}"; DestName: "INNO_SETUP_LICENSE.txt"; Flags: ignoreversion
Source: "INSTALLER_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\RegionCompositor"; Filename: "{app}\region_compositor.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\RegionCompositor"; Filename: "{app}\region_compositor.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\region_compositor.exe"; Description: "{cm:LaunchProgram,RegionCompositor}"; Flags: nowait postinstall skipifsilent
