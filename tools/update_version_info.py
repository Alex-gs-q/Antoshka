import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT / "core" / "version.py"
BUILD_DIR = ROOT / "build"
OUT_PATH = BUILD_DIR / "version_info.txt"

text = VERSION_PATH.read_text(encoding="utf-8")
match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
app_version = match.group(1) if match else "0.0.0"

parts = [int(p) if p.isdigit() else 0 for p in app_version.split(".")]
while len(parts) < 4:
    parts.append(0)
filevers = tuple(parts[:4])

BUILD_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(
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
                        StringStruct("InternalName", "AntoshkaApp"),
                        StringStruct("OriginalFilename", "AntoshkaApp.exe"),
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

print(f"[OK] version_info updated: {OUT_PATH} -> {app_version}")
