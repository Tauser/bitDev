import datetime


def fetch_agenda(state, http_client, calendar_cls, ical_available, logger):
    if not ical_available or calendar_cls is None:
        return
    if not state.get("agenda_url"):
        return

    try:
        response = http_client.get(state["agenda_url"], timeout=10)
        if response.status_code != 200:
            logger.warning("op=fetch_agenda status=http_error code=%s", response.status_code)
            return

        cal = calendar_cls.from_ical(response.content)
        events = []

        now = datetime.datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            summary_obj = component.get("summary")
            summary = str(summary_obj) if summary_obj else "Evento"

            dtstart_prop = component.get("dtstart")
            if not dtstart_prop:
                continue
            dtstart = dtstart_prop.dt

            if isinstance(dtstart, datetime.datetime):
                if dtstart.tzinfo is not None:
                    dtstart = dtstart.astimezone().replace(tzinfo=None)
            elif isinstance(dtstart, datetime.date):
                dtstart = datetime.datetime.combine(dtstart, datetime.time.min)

            if dtstart >= today_start:
                events.append({"summary": summary, "dt": dtstart})

        events.sort(key=lambda x: x["dt"])

        next_week = today_start + datetime.timedelta(days=7)
        events_week = [e for e in events if e["dt"] <= next_week]

        if events_week:
            state["agenda"] = events_week[:6]
        else:
            next_month = today_start + datetime.timedelta(days=30)
            events_month = [e for e in events if e["dt"] <= next_month]
            state["agenda"] = events_month[:6]
    except Exception as exc:
        logger.warning("op=fetch_agenda status=failed reason=%s", exc)