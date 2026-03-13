import time


def fetch_weather(state, http_client):
    cidade = state.get("cidade", "Sao_Paulo")

    if not state.get("manual_coords", False):
        if state.get("_cached_city") != cidade or "lat" not in state:
            try:
                cidade_query = cidade.replace("_", " ")
                geo_url = "https://geocoding-api.open-meteo.com/v1/search"
                params = {"name": cidade_query, "count": 1, "language": "pt", "format": "json"}

                geo_data = http_client.get(geo_url, params=params, timeout=3).json()
                if geo_data.get("results"):
                    state["lat"] = geo_data["results"][0]["latitude"]
                    state["lon"] = geo_data["results"][0]["longitude"]
                    state["_cached_city"] = cidade
            except Exception:
                pass

    if "lat" not in state:
        return

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": state["lat"],
            "longitude": state["lon"],
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature,is_day",
            "hourly": "uv_index,temperature_2m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
        }
        weather_data = http_client.get(url, params=params, timeout=3).json()

        utc_offset = weather_data.get("utc_offset_seconds", 0)
        local_hour = time.gmtime(time.time() + utc_offset).tm_hour

        curr = weather_data.get("current", {})
        daily = weather_data.get("daily", {})
        hourly = weather_data.get("hourly", {})

        if curr:
            t = int(round(curr["temperature_2m"]))
            state["temp"] = str(t)
            state["weather"]["temp"] = t
            state["weather"]["humidity"] = curr["relative_humidity_2m"]
            state["weather"]["wind"] = curr["wind_speed_10m"]
            state["weather"]["code"] = curr["weather_code"]
            state["weather"]["feels_like"] = int(round(curr.get("apparent_temperature", t)))
            state["weather"]["is_day"] = curr.get("is_day", 1)

        if hourly:
            if "uv_index" in hourly:
                idx = max(0, min(23, local_hour))
                state["weather"]["uv"] = hourly["uv_index"][idx]
            if "temperature_2m" in hourly:
                state["weather"]["hourly_temps"] = hourly["temperature_2m"][local_hour : local_hour + 12]

        if daily:
            state["weather"]["min"] = int(round(daily["temperature_2m_min"][0]))
            state["weather"]["max"] = int(round(daily["temperature_2m_max"][0]))
            state["weather"]["pop"] = int(round(daily["precipitation_probability_max"][0]))
    except Exception:
        pass