; Script gerado para Veritas Player
; Requer Inno Setup instalado

#define MyAppName "Veritas Player"
#define MyAppVersion "19.24"
#define MyAppPublisher "Gabriel Gouvea"
#define MyAppExeName "VeritasPlayer.exe"

[Setup]
; --- Identificação Única (Gere um GUID novo no Inno Setup se quiser) ---
; AppId precisa ser um GUID válido (apenas 0-9/A-F). Exemplo:
; AppId={{8A23C9B1-5D3A-4E1F-9C2B-7A8D6E5F4A3B}}

; GUID válido gerado para este instalador
AppId={{8A23C9B1-5D3A-4E1F-9C2B-7A8D6E5F4A3B}}

; --- Configurações Visuais ---
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=VeritasPlayer_Setup_v{#MyAppVersion}
OutputDir=Output
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; --- Comportamento de Atualização (CRÍTICO) ---
; Isso força o fechamento do app antes de instalar por cima
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; --- ARQUIVOS DO PYINSTALLER (Pasta dist/VeritasPlayer) ---
; Ajuste o caminho "C:\Zag_Project..." para a sua pasta real se for diferente
Source: "dist\VeritasPlayer\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\VeritasPlayer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; -----------------------------------------------------------

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent