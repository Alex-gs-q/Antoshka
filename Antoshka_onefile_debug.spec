# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import re

block_cipher = None
project_root = Path.cwd()

version_path = project_root / "core" / "version.py"
version_text = version_path.read_text(encoding="utf-8")
match = re.search(r'__version__\s*=\s*"([^"]+)"', version_text)
app_version = match.group(1) if match else "0.0.0"
parts = [int(p) if p.isdigit() else 0 for p in app_version.split(".")]
while len(parts) < 4:
    parts.append(0)
filevers = tuple(parts[:4])

build_dir = project_root / "build"
build_dir.mkdir(parents=True, exist_ok=True)
version_file = build_dir / "version_info.txt"
version_file.write_text(
    f"""VSVersionInfo(
    ffi=FixedFileInfo(
        filevers={filevers},
        prodvers={filevers},
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "Antoshka"),
                        StringStruct("FileDescription", "Antoshka Voice Assistant"),
                        StringStruct("FileVersion", "{app_version}"),
                        StringStruct("InternalName", "Antoshka_onefile_debug"),
                        StringStruct("OriginalFilename", "Antoshka_onefile_debug.exe"),
                        StringStruct("ProductName", "Antoshka"),
                        StringStruct("ProductVersion", "{app_version}"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [0x0409, 0x04B0])]),
    ],
)""",
    encoding="utf-8",
)

datas = [
    (str(project_root / "config"), "config"),
    (str(project_root / "data" / ".keep"), "data"),
    (str(project_root / "assets"), "assets"),
    (str(project_root / "img"), "img"),
    (str(project_root / "Music"), "Music"),
    (str(project_root / "models"), "models"),
]

a = Analysis(
    ["antoshka_ui.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "winrt.windows.ui.notifications",
        "winrt.windows.data.xml.dom",
        "winsdk.windows.ui.notifications",
        "winsdk.windows.data.xml.dom",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Antoshka_onefile_debug",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon=str(project_root / "assets" / "icons" / "app_icon_v3.ico"),
    version=str(version_file),
)
