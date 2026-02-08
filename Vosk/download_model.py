# download_model.py
import urllib.request
import zipfile
from pathlib import Path


def download_vosk_model():
    """Скачивание модели Vosk для русского языка"""

    print("📥 Скачивание модели Vosk...")

    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
    model_dir = Path("models")
    model_zip = model_dir / "vosk-model-small-ru.zip"

    # Создаем папку если ее нет
    model_dir.mkdir(exist_ok=True)

    try:
        # Скачиваем файл
        print(f"Скачиваю с {model_url}...")
        urllib.request.urlretrieve(model_url, model_zip)

        # Распаковываем
        print("Распаковываю...")
        with zipfile.ZipFile(model_zip, 'r') as zip_ref:
            zip_ref.extractall(model_dir)

        # Удаляем zip файл
        model_zip.unlink()

        print("✅ Модель успешно установлена!")
        print(f"📁 Путь: {model_dir.absolute()}/vosk-model-small-ru-0.22")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("⚠️  Скачайте модель вручную:")
        print("https://alphacephei.com/vosk/models")
        print("Распакуйте в папку models/")
        return False


if __name__ == "__main__":
    download_vosk_model()