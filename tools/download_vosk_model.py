import os
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
TARGET_DIR = Path("models") / "vosk"
ZIP_PATH = Path("models") / "vosk_model_ru.zip"


def main():
    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)

    if TARGET_DIR.exists() and any(TARGET_DIR.iterdir()):
        print(f"[OK] Model already exists in: {TARGET_DIR}")
        return

    print("[DL] Downloading model zip...")
    urlretrieve(MODEL_URL, ZIP_PATH)
    print(f"[OK] Downloaded: {ZIP_PATH}")

    print("[UNZIP] Extracting...")
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extractall(Path("models"))

    # After unzip, inside models/ will be a folder like vosk-model-small-ru-0.22
    extracted = None
    for p in Path("models").iterdir():
        if p.is_dir() and p.name.startswith("vosk-model"):
            extracted = p
            break

    if extracted is None:
        raise RuntimeError("Cannot find extracted vosk-model folder in models/")

    # Rename/move to models/vosk
    if TARGET_DIR.exists():
        # if somehow created, remove empty dir
        if not any(TARGET_DIR.iterdir()):
            TARGET_DIR.rmdir()

    extracted.rename(TARGET_DIR)
    print(f"[OK] Model installed to: {TARGET_DIR}")

    try:
        os.remove(ZIP_PATH)
    except OSError:
        pass


if __name__ == "__main__":
    main()
