from services.text.num_normalize import normalize_numbers


def test_ru_numbers_normalize():
    assert "5 минут" in normalize_numbers("поставь таймер на пять минут", "ru")
    assert "70" in normalize_numbers("громкость на семьдесят", "ru")
    assert "25 секунд" in normalize_numbers("через двадцать пять секунд", "ru")
    assert normalize_numbers("поставь таймер на 2 минуты", "ru") == "поставь таймер на 2 минуты"
    assert normalize_numbers("Антошка открой ютуб", "ru") == "Антошка открой ютуб"


def test_en_numbers_normalize():
    assert "5 minutes" in normalize_numbers("set a timer for five minutes", "en")
