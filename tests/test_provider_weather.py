from providers import weather as weather_provider


class DummyClient:
    def get(self, _url, params=None, **_kwargs):
        if "geocoding-api" in _url:
            payload = {"results": [{"latitude": -23.5, "longitude": -46.6}]}
        else:
            payload = {
                "utc_offset_seconds": 0,
                "current": {
                    "temperature_2m": 25.2,
                    "relative_humidity_2m": 70,
                    "weather_code": 1,
                    "wind_speed_10m": 12,
                    "apparent_temperature": 26.1,
                    "is_day": 1,
                },
                "hourly": {"uv_index": [1] * 24, "temperature_2m": [20 + i for i in range(24)]},
                "daily": {
                    "temperature_2m_min": [19],
                    "temperature_2m_max": [30],
                    "precipitation_probability_max": [40],
                },
            }
        return type("Resp", (), {"json": lambda _self: payload})()


def test_fetch_weather_updates_snapshot_fields():
    state = {
        "cidade": "Sao_Paulo",
        "manual_coords": False,
        "weather": {"temp": 0, "min": 0, "max": 0, "humidity": 0, "wind": 0, "code": 0, "uv": 0, "feels_like": 0, "hourly_temps": [], "is_day": 1, "pop": 0},
    }

    weather_provider.fetch_weather(state, DummyClient())

    assert state["temp"].isdigit()
    assert state["weather"]["temp"] > 0
    assert state["weather"]["max"] == 30
    assert state["weather"]["min"] == 19
    assert state["weather"]["pop"] == 40