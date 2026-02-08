from typing import Dict, Any


def handle(_: Dict[str, Any]) -> str:
    return (
        "Я Антошка. Команды MVP:\n"
        "- помощь\n"
        "- привет\n"
        "- который час / какая дата\n"
        "- открой ютуб / открой google / открой <url>\n"
        "- открой <путь>\n"
        "- выход"
    )