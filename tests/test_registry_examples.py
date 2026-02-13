from commands.builtins import create_registry



def test_registry_examples_match():
    reg = create_registry()
    for lang in ("ru", "en"):
        for example in reg.get_all_examples(lang):
            res = reg.match(example)
            assert res is not None, f"No match for {lang} example: {example!r}"
