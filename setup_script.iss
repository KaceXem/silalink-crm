[Setup]
AppName=SilaLink CRM
AppVersion=2.0.0
DefaultDirName={autopf}\SilaLinkCRM
DefaultGroupName=SilaLink CRM
OutputDir=.\InstallerOutput
OutputBaseFilename=SilaLink_Setup_v2.0
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
; 1. Le Hub principal compilé (qui gère le lancement silencieux)
Source: "dist\SilaLinkHub.exe"; DestDir: "{app}"; Flags: ignoreversion

; 2. Le code du backend FastAPI, la base de données et le service Gmail
Source: "src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs

; 3. L'interface React compilée (servie directement par FastAPI)
Source: "silalink-frontend\dist\*"; DestDir: "{app}\silalink-frontend\dist"; Flags: ignoreversion recursesubdirs createallsubdirs

; 4. Le proxy OmniRoute (uniquement les dossiers essentiels de production, sans les gros fichiers de build)
Source: "C:\Users\USER\Desktop\4 espace\OmniRoute-release-v3.8.51\dist\*"; DestDir: "{app}\OmniRoute\dist"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\Users\USER\Desktop\4 espace\OmniRoute-release-v3.8.51\src\*"; DestDir: "{app}\OmniRoute\src"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Création du raccourci dans le menu Démarrer et sur le Bureau avec votre icône personnalisée
Name: "{group}\SilaLink CRM"; Filename: "{app}\SilaLinkHub.exe"; IconFilename: "{app}\src\silalink.ico"
Name: "{autodesktop}\SilaLink CRM"; Filename: "{app}\SilaLinkHub.exe"; IconFilename: "{app}\src\silalink.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked