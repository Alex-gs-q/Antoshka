import re

# Слова-паразиты/вежливость — можно расширять
FILLER_WORDS_RU = {
    "пожалуйста",
    "пж",
    "плиз",
    "ну",
    "ээ",
    "эм",
    "короче",
    "типа",
}

# Простые замены синонимов (минимум для MVP)
REPLACEMENTS = {
    "youtube": "ютуб",
    "ютьюб": "ютуб",
    "you tube": "ютуб",
    "гугл": "google",  # можно наоборот, но пусть будет единообразно
}


def normalize_ru(text: str) -> str:
    """
    Нормализация русского текста для NLU (правила).
    1) lower
    2) ё->е
    3) убрать лишние пробелы
    4) убрать большую часть пунктуации
    5) применить простые замены (youtube->ютуб и т.п.)
    6) убрать слова-паразиты (минимальный список)
    """
    if not text:
        return ""

    s = text.strip().lower()
    s = s.replace("ё", "е")

    # заменить некоторые синонимы до чистки пунктуации
    for k, v in REPLACEMENTS.items():
        s = s.replace(k, v)

    # убрать всё, кроме букв/цифр/пробелов
    # (разрешаем дефис внутри слов: "по-русски")
    s = re.sub(r"[^\w\s\-]+", " ", s, flags=re.UNICODE)

    # заменить подчёркивания на пробелы (на всякий)
    s = s.replace("_", " ")

    # схлопнуть пробелы
    s = re.sub(r"\s+", " ", s).strip()

    if not s:
        return ""

    tokens = s.split()
    tokens = [t for t in tokens if t not in FILLER_WORDS_RU]

    return " ".join(tokens)
