from datetime import datetime, timedelta

from alerts.models import Event
from alerts.scheduler import AlertScheduler


def test_reschedule_updates_due_time():
    fired = []

    def _cb(ev):
        fired.append(ev)

    sched = AlertScheduler(on_event_fired=_cb)
    ev = Event(type="timer", due_time=datetime.now() + timedelta(minutes=10), payload={})
    sched.schedule_event(ev)
    new_due = datetime.now() + timedelta(minutes=20)
    assert sched.reschedule_event(ev.id, new_due) is True
    updated = sched.get_event(ev.id)
    assert updated is not None
    assert updated.due_time == new_due


def test_dismiss_event_marks_closed():
    fired = []

    def _cb(ev):
        fired.append(ev)

    sched = AlertScheduler(on_event_fired=_cb)
    ev = Event(type="reminder", due_time=datetime.now() + timedelta(minutes=10), payload={})
    sched.schedule_event(ev)
    assert sched.dismiss_event(ev.id) is True
    updated = sched.get_event(ev.id)
    assert updated is not None
    assert updated.dismissed is True


def test_restart_timer_creates_new_event():
    fired = []

    def _cb(ev):
        fired.append(ev)

    sched = AlertScheduler(on_event_fired=_cb)
    ev = Event(type="timer", due_time=datetime.now() + timedelta(minutes=10), payload={}, duration_sec=60)
    sched.schedule_event(ev)
    new_id = sched.restart_timer(ev.id)
    assert new_id is not None
    assert new_id != ev.id
