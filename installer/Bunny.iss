; Bunny - offline AI desk buddy. Built by GitHub Actions (see .github/workflows/build.yml)
#define AppVer GetEnv("BUNNY_VERSION")
#if AppVer == ""
  #define AppVer "0.1.0"
#endif

[Setup]
AppId={{9B3E6F41-2C7A-4E58-8D1B-6A0F3C2E7B95}
AppName=Bunny
AppVersion={#AppVer}
AppPublisher=Akash Sisodiya
DefaultDirName={autopf}\Bunny
DefaultGroupName=Bunny
OutputDir=..\out
OutputBaseFilename=Bunny-Setup
Compression=lzma2/fast
SolidCompression=no
DiskSpanning=no
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
WizardStyle=modern
SetupIconFile=bunny.ico
UninstallDisplayIcon={app}\Bunny.exe

[Tasks]
Name: "ollama"; Description: "Install Ollama (Bunny's offline AI brain, free, about 1 GB) - skip if you already have it"; Check: not OllamaInstalled
Name: "firewall"; Description: "Security lock: block Bunny from the internet (recommended - Bunny never needs it)"
Name: "autostart"; Description: "Start Bunny when Windows starts"
Name: "desktopicon"; Description: "Desktop shortcut"

[Files]
Source: "..\dist\Bunny\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Bunny"; Filename: "{app}\Bunny.exe"; IconFilename: "{app}\Bunny.exe"
Name: "{group}\Uninstall Bunny"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Bunny"; Filename: "{app}\Bunny.exe"; Tasks: desktopicon
Name: "{userstartup}\Bunny"; Filename: "{app}\Bunny.exe"; Tasks: autostart; Flags: runminimized

[Run]
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""Bunny - no internet"" dir=out action=block program=""{app}\Bunny.exe"" enable=yes"; Flags: runhidden; Tasks: firewall; StatusMsg: "Adding the security lock..."
Filename: "{app}\Bunny.exe"; Description: "Start Bunny now"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""Bunny - no internet"""; Flags: runhidden; RunOnceId: "fw"

[Code]
var
  DownloadPage: TDownloadWizardPage;

function OllamaInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe')) or
            FileExists(ExpandConstant('{autopf}\Ollama\ollama.exe'));
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage('Downloading Ollama', 'Bunny''s offline AI brain', nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if (CurPageID = wpReady) and WizardIsTaskSelected('ollama') then begin
    DownloadPage.Clear;
    DownloadPage.Add('https://ollama.com/download/OllamaSetup.exe', 'OllamaSetup.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
        Exec(ExpandConstant('{tmp}\OllamaSetup.exe'), '/VERYSILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_SHOW,
             ewWaitUntilTerminated, ResultCode);
      except
        MsgBox('Ollama could not be downloaded (' + GetExceptionMessage + ').' + #13#10 +
               'Bunny will still install. Get Ollama later from ollama.com.', mbInformation, MB_OK);
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;
