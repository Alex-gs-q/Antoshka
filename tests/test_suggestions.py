import random

from commands.builtins import create_registry
from core.suggestions import pick_suggestions



def test_pick_suggestions_from_registry():
    reg = create_registry()
    for lang in ("ru", "en"):
        random.seed(0)
        picked = pick_suggestions(reg, lang=lang, context="default", k=5)
        assert len(picked) == 5
        allowed = set(reg.get_all_examples(lang))
        assert all(item in allowed for item in picked)
