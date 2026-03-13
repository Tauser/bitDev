import datetime

from providers import agenda as agenda_provider


class DummyResp:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content


class DummyClient:
    def get(self, _url, **_kwargs):
        return DummyResp(200, b"ics")


class DummyEvent:
    def __init__(self, dt, summary="Evento"):
        self.name = "VEVENT"
        self._dt = dt
        self._summary = summary

    def get(self, key):
        if key == "summary":
            return self._summary
        if key == "dtstart":
            return type("D", (), {"dt": self._dt})()
        return None


class DummyCalendar:
    @staticmethod
    def from_ical(_content):
        now = datetime.datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        class C:
            def walk(self):
                return [DummyEvent(now + datetime.timedelta(days=1), "Teste")]
        return C()


class DummyLogger:
    def warning(self, *_args, **_kwargs):
        return None


def test_fetch_agenda_populates_upcoming_events():
    state = {"agenda_url": "http://example/ics", "agenda": []}

    agenda_provider.fetch_agenda(state, DummyClient(), DummyCalendar, True, DummyLogger())

    assert len(state["agenda"]) == 1
    assert state["agenda"][0]["summary"] == "Teste"


def test_fetch_agenda_noop_when_unavailable():
    state = {"agenda_url": "http://example/ics", "agenda": []}
    agenda_provider.fetch_agenda(state, DummyClient(), None, False, DummyLogger())
    assert state["agenda"] == []