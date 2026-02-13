import json
import re
from pathlib import Path


def test_phrases_ru_utf8_and_cyrillic():
    path = Path("config/phrases_ru.json")
    data = path.read_bytes()
    text = data.decode("utf-8")
    # must contain Cyrillic
    assert re.search(r"[А-яЁё]", text) is not None
    # must be valid JSON
    json.loads(text)
