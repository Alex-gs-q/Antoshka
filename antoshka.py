from core.config import load_settings
from core.dialogue import Dialogue, DialogueConfig
from core.logger import setup_logger


def main():
    logger = setup_logger()
    settings = load_settings()

    dangerous_mode = bool(settings.get("safety", {}).get("dangerous_mode", False))

    logger.info("Antoshka started")
    logger.info("STT mode: text")
    logger.info("Dangerous mode: %s", dangerous_mode)

    dialogue = Dialogue(DialogueConfig(dangerous_mode=dangerous_mode))

    print("Антошка: текстовый режим. Напиши команду (или 'помощь'). Для выхода: 'выход'.")

    while True:
        try:
            text = input("Ты: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nАнтошка: пока!")
            break

        answer = dialogue.handle_text(text)

        if answer == "__EXIT__":
            print("Антошка: пока!")
            break

        print(f"Антошка: {answer}")


if __name__ == "__main__":
    main()
