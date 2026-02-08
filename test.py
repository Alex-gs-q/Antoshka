pip install vosk pyttsx3 pyaudio


import json
import os
import sys
import time
import threading
import logging
import subprocess
import webbrowser
import re
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


# ==================== БАЗОВЫЕ КЛАССЫ ====================
class AppState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class RecognitionResult:
    text: str
    confidence: float
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


# ==================== КОНФИГУРАЦИЯ ====================
class Config:
    """Простая конфигурация"""

    DEFAULT_CONFIG = {
        "version": "1.0",
        "model_path": "models/vosk-model-small-ru",
        "sample_rate": 16000,
        "trigger_word": "антошка",
        "tts_rate": 175,
        "tts_volume": 0.9,
        "security": {
            "confirmation_timeout": 10,
            "confirmation_words": ["подтверждаю", "да", "согласен"],
            "cancel_words": ["отмена", "нет", "стоп"]
        },
        "paths": {
            "allowed": ["~/Documents", "~/Downloads", "~/Desktop"],
            "blocked": []
        }
    }

    def __init__(self, config_path="config/settings.json"):
        self.config_path = Path(config_path)
        self.data = self.load()

    def load(self):
        """Загрузка конфигурации"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        # Создаем дефолтную конфигурацию
        self.save(self.DEFAULT_CONFIG)
        return self.DEFAULT_CONFIG.copy()

    def save(self, config=None):
        """Сохранение конфигурации"""
        if config is None:
            config = self.data

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        """Получение значения"""
        keys = key.split('.')
        value = self.data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value


# ==================== ЛОГГЕР ====================
class SimpleLogger:
    """Простой логгер"""

    def __init__(self, log_file="logs/antoshka.log"):
        self.log_file = Path(log_file)
        self.setup()

    def setup(self):
        """Настройка логгера"""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("Antoshka")

    def info(self, message, data=None):
        if data:
            self.logger.info(f"{message}: {json.dumps(data, ensure_ascii=False)}")
        else:
            self.logger.info(message)

    def error(self, message, data=None):
        if data:
            self.logger.error(f"{message}: {json.dumps(data, ensure_ascii=False)}")
        else:
            self.logger.error(message)


# ==================== VOSK STT ====================
class VoskSTT:
    """Распознавание речи через Vosk"""

    def __init__(self, model_path, sample_rate=16000):
        try:
            from vosk import Model, KaldiRecognizer
            self.vosk_available = True
        except ImportError:
            print("Vosk не установлен. Установите: pip install vosk")
            self.vosk_available = False
            return

        self.model_path = Path(model_path)
        self.sample_rate = sample_rate

        if not self.model_path.exists():
            print(f"Модель Vosk не найдена: {model_path}")
            print("Скачайте с: https://alphacephei.com/vosk/models")
            self.vosk_available = False
            return

        try:
            self.model = Model(str(self.model_path))
            self.recognizer = KaldiRecognizer(self.model, sample_rate)
            self.vosk_available = True
        except Exception as e:
            print(f"Ошибка инициализации Vosk: {e}")
            self.vosk_available = False

    def listen(self, duration=5):
        """Прослушивание и распознавание речи"""
        if not self.vosk_available:
            return None

        try:
            import pyaudio

            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=1024
            )

            print(f"🎤 Говорите {duration} секунд...")
            frames = []

            for _ in range(0, int(self.sample_rate / 1024 * duration)):
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)

            stream.stop_stream()
            stream.close()
            p.terminate()

            audio_data = b''.join(frames)

            if self.recognizer.AcceptWaveform(audio_data):
                result = json.loads(self.recognizer.Result())
                text = result.get('text', '').strip()
                confidence = float(result.get('confidence', 0.0))

                if text:
                    return RecognitionResult(text=text, confidence=confidence)

            return None

        except ImportError:
            print("Pyaudio не установлен. Установите: pip install pyaudio")
            return None
        except Exception as e:
            print(f"Ошибка при прослушивании: {e}")
            return None


# ==================== TTS ====================
class TTS:
    """Синтез речи"""

    def __init__(self, rate=175, volume=0.9):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            self.available = True
        except Exception as e:
            print(f"Ошибка инициализации TTS: {e}")
            self.available = False

    def speak(self, text):
        """Озвучивание текста"""
        if not self.available:
            print(f"📢 (TTS): {text}")
            return

        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Ошибка синтеза речи: {e}")


# ==================== СИСТЕМА ИНТЕНТОВ ====================
class IntentSystem:
    """Система распознавания намерений"""

    def __init__(self):
        # Словарь интентов
        self.intents = {
            "HELP": {
                "patterns": ["помощь", "что ты умеешь", "справка", "команды"],
                "response": "Я умею: сказать время, открыть сайт, запустить программы, поставить таймер."
            },
            "TIME": {
                "patterns": ["который час", "время", "сколько времени", "скажи время"],
                "response": "Сейчас {time}"
            },
            "DATE": {
                "patterns": ["какая сегодня дата", "дата", "число"],
                "response": "Сегодня {date}"
            },
            "OPEN_URL": {
                "patterns": ["открой сайт", "открой ссылку", "перейди на"],
                "response": "Открываю {url}"
            },
            "SEARCH": {
                "patterns": ["найди", "поищи", "ищи в интернете"],
                "response": "Ищу {query}"
            },
            "OPEN_APP": {
                "patterns": ["запусти", "открой программу", "включи"],
                "response": "Запускаю {app}"
            },
            "TIMER": {
                "patterns": ["поставь таймер", "таймер на", "засеки время"],
                "response": "Таймер на {minutes} минут установлен"
            },
            "CALCULATOR": {
                "patterns": ["калькулятор", "посчитай"],
                "response": "Открываю калькулятор"
            },
            "GREETING": {
                "patterns": ["привет", "здравствуй", "добрый день"],
                "response": "Привет! Я Антошка. Чем могу помочь?"
            },
            "EXIT": {
                "patterns": ["выход", "закройся", "пока"],
                "response": "До свидания!"
            }
        }

    def recognize(self, text):
        """Распознавание интента"""
        text_lower = text.lower()

        for intent_name, intent_data in self.intents.items():
            for pattern in intent_data["patterns"]:
                if pattern in text_lower:
                    return intent_name, intent_data

        return None, None

    def extract_slots(self, intent_name, text):
        """Извлечение параметров"""
        slots = {}
        text_lower = text.lower()

        if intent_name == "TIMER":
            # Поиск числа для таймера
            numbers = re.findall(r'\b\d+\b', text_lower)
            if numbers:
                slots["minutes"] = int(numbers[0])
            else:
                # Попытка распознать словами
                number_words = {
                    'один': 1, 'два': 2, 'три': 3, 'четыре': 4, 'пять': 5,
                    'шесть': 6, 'семь': 7, 'восемь': 8, 'девять': 9, 'десять': 10
                }
                for word, num in number_words.items():
                    if word in text_lower:
                        slots["minutes"] = num
                        break

        elif intent_name == "OPEN_URL":
            # Извлечение сайта или запроса
            sites = {
                "youtube": "https://youtube.com",
                "google": "https://google.com",
                "вконтакте": "https://vk.com",
                "яндекс": "https://yandex.ru",
                "почта": "https://mail.ru"
            }

            for site_name, url in sites.items():
                if site_name in text_lower:
                    slots["url"] = url
                    break

            if "url" not in slots:
                # Если сайт не найден, используем поиск
                query = text_lower
                for phrase in ["открой сайт", "открой", "сайт"]:
                    query = query.replace(phrase, "").strip()
                if query:
                    slots["url"] = f"https://www.google.com/search?q={query}"

        elif intent_name == "SEARCH":
            # Извлечение поискового запроса
            query = text_lower
            for phrase in ["найди", "поищи", "ищи"]:
                query = query.replace(phrase, "").strip()
            if query:
                slots["query"] = query

        elif intent_name == "OPEN_APP":
            # Извлечение названия приложения
            apps = ["калькулятор", "блокнот", "браузер", "проводник"]
            for app in apps:
                if app in text_lower:
                    slots["app"] = app
                    break

        return slots


# ==================== СИСТЕМА БЕЗОПАСНОСТИ ====================
class SafetySystem:
    """Простая система безопасности"""

    def __init__(self, config):
        self.config = config
        self.pending_action = None
        self.pending_since = None

    def check_action(self, intent_name):
        """Проверка необходимости подтверждения"""
        dangerous_intents = ["DELETE", "SHUTDOWN", "FORMAT"]

        if intent_name in dangerous_intents:
            return True
        return False

    def request_confirmation(self, intent_name, slots):
        """Запрос подтверждения"""
        self.pending_action = {
            "intent": intent_name,
            "slots": slots
        }
        self.pending_since = time.time()

        return "Для выполнения этой команды скажите 'подтверждаю' или 'отмена'"

    def process_confirmation(self, text):
        """Обработка подтверждения"""
        if not self.pending_action:
            return "no_pending"

        text_lower = text.lower()
        timeout = self.config.get("security.confirmation_timeout", 10)

        # Проверка таймаута
        if time.time() - self.pending_since > timeout:
            self.pending_action = None
            return "timeout"

        # Проверка подтверждения
        confirm_words = self.config.get("security.confirmation_words", [])
        cancel_words = self.config.get("security.cancel_words", [])

        if any(word in text_lower for word in confirm_words):
            action = self.pending_action
            self.pending_action = None
            return "confirmed", action

        elif any(word in text_lower for word in cancel_words):
            self.pending_action = None
            return "cancelled"

        return "waiting"


# ==================== МЕНЕДЖЕР НАВЫКОВ ====================
class SkillManager:
    """Управление навыками"""

    def __init__(self, tts, config):
        self.tts = tts
        self.config = config
        self.timer_thread = None
        self.notes_file = Path("notes.txt")

    def execute(self, intent_name, slots):
        """Выполнение навыка"""

        if intent_name == "HELP":
            return self.help()

        elif intent_name == "TIME":
            now = datetime.now().strftime("%H:%M")
            return f"Сейчас {now}"

        elif intent_name == "DATE":
            today = datetime.now().strftime("%d.%m.%Y")
            return f"Сегодня {today}"

        elif intent_name == "OPEN_URL":
            url = slots.get("url", "https://google.com")
            webbrowser.open(url)
            return f"Открываю {url}"

        elif intent_name == "SEARCH":
            query = slots.get("query", "")
            if query:
                url = f"https://www.google.com/search?q={query}"
                webbrowser.open(url)
                return f"Ищу {query}"
            return "Что искать?"

        elif intent_name == "OPEN_APP":
            app_name = slots.get("app", "")
            if app_name == "калькулятор":
                if sys.platform == "win32":
                    os.system("calc")
                elif sys.platform == "darwin":
                    os.system("open -a Calculator")
                else:
                    os.system("gnome-calculator")
                return "Открываю калькулятор"
            return f"Не знаю как открыть {app_name}"

        elif intent_name == "TIMER":
            minutes = slots.get("minutes", 5)

            def timer_task():
                time.sleep(minutes * 60)
                self.tts.speak(f"Таймер на {minutes} минут завершен!")

            self.timer_thread = threading.Thread(target=timer_task)
            self.timer_thread.start()
            return f"Таймер на {minutes} минут установлен"

        elif intent_name == "CALCULATOR":
            if sys.platform == "win32":
                os.system("calc")
            elif sys.platform == "darwin":
                os.system("open -a Calculator")
            else:
                os.system("gnome-calculator")
            return "Открываю калькулятор"

        elif intent_name == "GREETING":
            greetings = [
                "Привет! Я Антошка.",
                "Здравствуйте! Чем могу помочь?",
                "Приветствую! Слушаю вас."
            ]
            return random.choice(greetings)

        elif intent_name == "EXIT":
            return "exit"

        return "Не понял команду. Скажите 'помощь' для списка команд."

    def help(self):
        """Показ помощи"""
        help_text = """
        Доступные команды:
        • Привет - поздороваться
        • Время - узнать текущее время
        • Дата - узнать сегодняшнюю дату
        • Открой сайт [название] - открыть сайт
        • Найди [запрос] - поиск в интернете
        • Запусти калькулятор - открыть калькулятор
        • Таймер на [число] минут - установить таймер
        • Выход - завершить работу
        """
        return help_text


# ==================== ОСНОВНОЙ КЛАСС ====================
class Antoshka:
    """Главный класс голосового помощника"""

    def __init__(self):
        # Инициализация компонентов
        self.config = Config()
        self.logger = SimpleLogger()
        self.tts = TTS(
            rate=self.config.get("tts_rate", 175),
            volume=self.config.get("tts_volume", 0.9)
        )
        self.stt = VoskSTT(
            model_path=self.config.get("model_path"),
            sample_rate=self.config.get("sample_rate", 16000)
        )
        self.intent_system = IntentSystem()
        self.safety = SafetySystem(self.config)
        self.skills = SkillManager(self.tts, self.config)

        self.state = AppState.IDLE
        self.running = True
        self.trigger_word = self.config.get("trigger_word", "антошка")

    def run(self):
        """Основной цикл работы"""
        print("=" * 50)
        print("🎤 Голосовой помощник АНТОШКА запущен")
        print("=" * 50)
        print(f"Триггер-слово: '{self.trigger_word}'")
        print("Примеры команд:")
        print("  • Антошка, который час?")
        print("  • Антошка, открой YouTube")
        print("  • Антошка, поставь таймер на 5 минут")
        print("  • Антошка, выход")
        print("=" * 50)

        self.tts.speak("Антошка запущен. Скажите 'Антошка' и команду.")

        try:
            while self.running:
                # Слушаем команду
                self.state = AppState.LISTENING
                result = self.stt.listen(duration=5)

                if not result or not result.text:
                    continue

                self.logger.info("Распознано", {"текст": result.text})

                # Проверка триггер-слова
                text_lower = result.text.lower()
                if self.trigger_word not in text_lower:
                    continue

                # Удаляем триггер-слово
                command = text_lower.replace(self.trigger_word, "").strip()

                # Проверка подтверждения опасных действий
                if self.safety.pending_action:
                    confirmation_result = self.safety.process_confirmation(command)

                    if confirmation_result == "confirmed":
                        action = self.safety.pending_action
                        response = self.skills.execute(action["intent"], action["slots"])
                        self.tts.speak("Подтверждено. Выполняю.")
                        continue
                    elif confirmation_result == "cancelled":
                        self.tts.speak("Команда отменена")
                        continue
                    elif confirmation_result == "timeout":
                        self.tts.speak("Время подтверждения истекло")
                        continue

                # Распознавание интента
                self.state = AppState.PROCESSING
                intent_name, intent_data = self.intent_system.recognize(command)

                if not intent_name:
                    self.tts.speak("Не понял команду. Скажите 'помощь' для списка команд.")
                    continue

                # Извлечение параметров
                slots = self.intent_system.extract_slots(intent_name, command)

                # Проверка безопасности
                if self.safety.check_action(intent_name):
                    self.state = AppState.PROCESSING
                    self.tts.speak(self.safety.request_confirmation(intent_name, slots))
                    continue

                # Выполнение команды
                response = self.skills.execute(intent_name, slots)

                if response == "exit":
                    self.tts.speak("До свидания!")
                    self.running = False
                else:
                    self.state = AppState.SPEAKING
                    self.tts.speak(response)

        except KeyboardInterrupt:
            print("\n👋 Завершение работы...")
            self.tts.speak("Завершаю работу")
        except Exception as e:
            self.logger.error("Ошибка", {"error": str(e)})
            self.tts.speak("Произошла ошибка")


# ==================== ЗАПУСК ====================
def check_dependencies():
    """Проверка зависимостей"""
    required = ["vosk", "pyttsx3", "pyaudio"]
    missing = []

    for package in required:
        try:
            if package == "vosk":
                from vosk import Model
            elif package == "pyttsx3":
                import pyttsx3
            elif package == "pyaudio":
                import pyaudio
        except ImportError:
            missing.append(package)

    return missing


def download_model():
    """Скачивание модели Vosk"""
    import urllib.request
    import zipfile

    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
    model_dir = Path("models")
    model_zip = model_dir / "vosk-model-small-ru.zip"

    if not model_dir.exists():
        model_dir.mkdir(parents=True)

    print("Скачивание модели Vosk...")
    try:
        urllib.request.urlretrieve(model_url, model_zip)
        print("Распаковка...")
        with zipfile.ZipFile(model_zip, 'r') as zip_ref:
            zip_ref.extractall(model_dir)
        model_zip.unlink()
        print("Модель успешно установлена!")
        return True
    except Exception as e:
        print(f"Ошибка загрузки модели: {e}")
        return False


def main():
    """Главная функция"""
    print("Проверка зависимостей...")
    missing = check_dependencies()

    if missing:
        print(f"Отсутствуют зависимости: {', '.join(missing)}")
        print("Установите: pip install " + " ".join(missing))
        return

    # Проверка модели Vosk
    model_path = Path("models/vosk-model-small-ru")
    if not model_path.exists():
        print("Модель Vosk не найдена.")
        response = input("Скачать модель? (y/n): ")
        if response.lower() == 'y':
            if not download_model():
                print("Не удалось скачать модель.")
                return
        else:
            print("Для работы нужна модель Vosk.")
            return

    # Запуск помощника
    assistant = Antoshka()
    assistant.run()


if __name__ == "__main__":
    main()