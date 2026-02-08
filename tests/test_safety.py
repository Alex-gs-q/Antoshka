from core.safety import SafetyGate, Action


def test_safety_deny():

    gate = SafetyGate(dangerous_mode=False, confirm_phrase="ok", confirm_ttl_seconds=1)

    res = gate.check(Action("delete_file", {}))

    assert res.decision.value == "deny"


def test_safety_unknown_deny():

    gate = SafetyGate(dangerous_mode=False, confirm_phrase="ok", confirm_ttl_seconds=1)

    res = gate.check(Action("unknown_action", {}))

    assert res.decision.value == "deny"


def test_safety_allow():

    gate = SafetyGate(dangerous_mode=False, confirm_phrase="ok", confirm_ttl_seconds=1)

    res = gate.check(Action("time", {}))

    assert res.decision.value == "allow"


def test_safety_need_confirm():

    gate = SafetyGate(dangerous_mode=False, confirm_phrase="ok", confirm_ttl_seconds=1)

    res = gate.check(Action("open_system_folder", {}))

    assert res.decision.value == "need_confirm"

    gate.confirm("ok")

    res2 = gate.check(Action("open_system_folder", {}))

    assert res2.decision.value == "allow"
