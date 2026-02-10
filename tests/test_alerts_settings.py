from alerts.settings import get_alert_settings


def test_alert_settings_defaults():
    settings = {"ui": {}}
    res = get_alert_settings(settings)
    assert res["snooze_default_minutes"] == 5
    assert res["snooze_quick_enabled"] is True
    assert 5 in res["snooze_quick_buttons"]
    assert res["snooze_dropdown_enabled"] is True
    assert 30 in res["snooze_dropdown_options"]
