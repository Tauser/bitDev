from providers.printer import PrinterProvider


class DummyCfg:
    C_TEAL = object()
    C_GREEN = object()
    C_RED = object()


class DummyLogger:
    def warning(self, *_args, **_kwargs):
        return None


class DummyClient:
    def __init__(self):
        self.calls = []

    def get(self, url, **_kwargs):
        self.calls.append(url)
        if url.endswith('/printer/objects/list'):
            payload = {"result": {"objects": ["print_stats", "display_status", "extruder", "heater_bed", "fan", "toolhead", "gcode_move", "quad_gantry_level"]}}
            return type("R", (), {"status_code": 200, "json": lambda _self: payload})()
        if '/printer/objects/query?' in url:
            payload = {
                "result": {
                    "status": {
                        "print_stats": {"state": "printing", "filename": "a.gcode", "print_duration": 10, "total_duration": 20},
                        "display_status": {"progress": 0.5, "message": "ok"},
                        "extruder": {"temperature": 200, "target": 210, "power": 0.6},
                        "heater_bed": {"temperature": 60, "target": 65, "power": 0.4},
                        "fan": {"speed": 0.5},
                        "toolhead": {"position": [1, 2, 3], "homed_axes": "xyz"},
                        "gcode_move": {"speed": 120, "speed_factor": 1.0, "extrude_factor": 1.0},
                        "quad_gantry_level": {"applied": True},
                    }
                }
            }
            return type("R", (), {"status_code": 200, "json": lambda _self: payload})()
        if '/server/files/metadata' in url:
            return type("R", (), {"status_code": 200, "json": lambda _self: {"result": {}}})()
        if '/server/history/totals' in url:
            payload = {"result": {"job_totals": {"total_time": 1, "total_filament_used": 2, "total_jobs": 3}}}
            return type("R", (), {"status_code": 200, "json": lambda _self: payload})()
        raise AssertionError(url)


def _base_state(printer_ip="192.168.1.10"):
    return {
        "printer_ip": printer_ip,
        "status": {"printer": False},
        "printer": {
            "state": "OFF",
            "progress": 0,
            "ext_actual": 0,
            "ext_target": 0,
            "bed_actual": 0,
            "bed_target": 0,
            "z_height": 0,
            "fan_speed": 0,
            "print_duration": 0,
            "total_duration": 0,
            "filename": "",
            "homed_axes": "",
            "print_speed": 0,
            "message": "",
            "is_moving": False,
            "sensors": {},
            "qgl_applied": False,
            "position": [0, 0, 0],
            "stats": {"total_time": 0, "total_filament": 0, "total_jobs": 0},
        },
    }


def test_printer_provider_marks_offline_without_ip():
    provider = PrinterProvider()
    state = _base_state("")

    provider.fetch(state, DummyClient(), lambda *_args, **_kwargs: None, DummyCfg(), DummyLogger())

    assert state["printer"]["state"] == "OFFLINE"
    assert state["status"]["printer"] is False


def test_printer_provider_updates_state_on_success():
    provider = PrinterProvider()
    state = _base_state()

    provider.fetch(state, DummyClient(), lambda *_args, **_kwargs: None, DummyCfg(), DummyLogger())

    assert state["status"]["printer"] is True
    assert state["printer"]["state"] == "printing"
    assert state["printer"]["progress"] == 50.0
    assert state["printer"]["stats"]["total_jobs"] == 3