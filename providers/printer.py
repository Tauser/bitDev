
class PrinterProvider:
    def __init__(self):
        self._cached_url = None
        self._fail_count = 0
        self._query_keys = []
        self._current_file = None
        self._file_metadata = {}

    def fetch(self, state, http_client, add_notification, cfg, logger):
        raw_ip = state.get("printer_ip", "").strip()
        printer_state = state["printer"]

        if not raw_ip:
            printer_state["state"] = "OFFLINE"
            state["status"]["printer"] = False
            return

        ip = raw_ip.replace("http://", "").replace("https://", "").rstrip("/")

        candidates = []
        if self._cached_url and ip in self._cached_url:
            candidates.append(self._cached_url)

        defaults = [f"http://{ip}", f"http://{ip}:7125"]
        if ":" in ip:
            defaults = [f"http://{ip}"]

        for url in defaults:
            if url not in candidates:
                candidates.append(url)

        success = False
        r_json = None

        for base_url in candidates:
            try:
                if not self._query_keys:
                    try:
                        r_list = http_client.get(f"{base_url}/printer/objects/list", timeout=2)
                        if r_list.status_code == 200:
                            all_objs = r_list.json().get("result", {}).get("objects", [])
                            keys = [
                                "print_stats",
                                "display_status",
                                "extruder",
                                "heater_bed",
                                "fan",
                                "toolhead",
                                "gcode_move",
                                "quad_gantry_level",
                            ]
                            for obj in all_objs:
                                if obj.startswith("temperature_sensor") or obj.startswith("temperature_fan") or obj.startswith("heater_generic"):
                                    keys.append(obj)
                            self._query_keys = keys
                    except Exception:
                        pass

                q_keys = self._query_keys or [
                    "print_stats",
                    "display_status",
                    "extruder",
                    "heater_bed",
                    "fan",
                    "toolhead",
                    "gcode_move",
                    "quad_gantry_level",
                ]

                url = f"{base_url}/printer/objects/query?" + "&".join(q_keys)
                response = http_client.get(url, timeout=2)
                if response.status_code == 200:
                    try:
                        payload = response.json()
                        if "result" in payload:
                            r_json = payload
                            success = True
                            self._cached_url = base_url
                            self._fail_count = 0
                            break
                    except Exception:
                        pass
            except Exception:
                continue

        if not success or not r_json:
            self._fail_count += 1
            self._cached_url = None
            self._query_keys = []
            if self._fail_count >= 5:
                printer_state["state"] = "OFFLINE"
                state["status"]["printer"] = False
            return

        try:
            res = r_json.get("result", {}).get("status", {})
            p_stats = res.get("print_stats", {})
            disp = res.get("display_status", {})
            ext = res.get("extruder", {})
            bed = res.get("heater_bed", {})
            fan = res.get("fan", {})
            tool = res.get("toolhead", {})
            move = res.get("gcode_move", {})

            filename = p_stats.get("filename", "")
            if filename and filename != self._current_file:
                self._current_file = filename
                self._file_metadata = {}
                try:
                    meta_url = f"{self._cached_url}/server/files/metadata?filename={filename}"
                    r_meta = http_client.get(meta_url, timeout=1)
                    if r_meta.status_code == 200:
                        self._file_metadata = r_meta.json().get("result", {})
                except Exception:
                    pass
            elif not filename:
                self._current_file = None
                self._file_metadata = {}

            current_state = p_stats.get("state", "error")
            last_state = printer_state.get("_last_state", "")

            if last_state and current_state != last_state:
                if current_state == "printing" and last_state != "paused":
                    add_notification(f"Imprimindo: {p_stats.get('filename', '')}", cfg.C_TEAL, 10)
                elif current_state == "complete":
                    add_notification("Impressao Finalizada!", cfg.C_GREEN, 60)
                elif current_state == "error":
                    add_notification("Erro na Impressora!", cfg.C_RED, 60)

            printer_state["_last_state"] = current_state

            printer_state["state"] = current_state
            printer_state["progress"] = float(disp.get("progress", 0)) * 100
            printer_state["filename"] = p_stats.get("filename", "")
            printer_state["message"] = str(disp.get("message") or "")
            printer_state["print_duration"] = p_stats.get("print_duration", 0)
            printer_state["total_duration"] = p_stats.get("total_duration", 0)

            info = p_stats.get("info") or {}
            current_layer = info.get("current_layer")
            total_layer = info.get("total_layer")

            if (not current_layer or not total_layer) and self._file_metadata:
                z_height = (tool.get("position") or [0, 0, 0])[2]
                layer_h = self._file_metadata.get("layer_height", 0)
                obj_h = self._file_metadata.get("object_height", 0)
                first_layer_h = self._file_metadata.get("first_layer_height", layer_h)

                if layer_h > 0:
                    if not total_layer and obj_h > 0:
                        total_layer = int(obj_h / layer_h)
                    if not current_layer and z_height > 0:
                        current_layer = 1 if z_height <= first_layer_h else 1 + int((z_height - first_layer_h) / layer_h)

            printer_state["layer"] = int(current_layer or 0)
            printer_state["total_layers"] = int(total_layer or 0)

            printer_state["ext_actual"] = ext.get("temperature", 0)
            printer_state["ext_target"] = ext.get("target", 0)
            printer_state["bed_actual"] = bed.get("temperature", 0)
            printer_state["bed_target"] = bed.get("target", 0)

            printer_state["ext_power"] = int((ext.get("power") or 0) * 100)
            printer_state["bed_power"] = int((bed.get("power") or 0) * 100)
            printer_state["speed_factor"] = int((move.get("speed_factor") or 1) * 100)
            printer_state["flow_factor"] = int((move.get("extrude_factor") or 1) * 100)

            printer_state["fan_speed"] = int((fan.get("speed") or 0) * 100)
            printer_state["z_height"] = (tool.get("position") or [0, 0, 0])[2]
            printer_state["homed_axes"] = tool.get("homed_axes") or ""
            printer_state["print_speed"] = int(move.get("speed") or 0)
            printer_state["position"] = tool.get("position", [0, 0, 0])
            printer_state["qgl_applied"] = res.get("quad_gantry_level", {}).get("applied", False)

            printer_state["sensors"] = {}
            for key, val in res.items():
                if key.startswith("temperature_sensor"):
                    printer_state["sensors"][key.replace("temperature_sensor ", "")] = val.get("temperature", 0)
                elif key.startswith("temperature_fan"):
                    printer_state["sensors"][key.replace("temperature_fan ", "")] = val.get("temperature", 0)
                elif key.startswith("heater_generic"):
                    printer_state["sensors"][key.replace("heater_generic ", "")] = val.get("temperature", 0)

            raw_pos = tool.get("position", [0, 0, 0])
            current_xyz = raw_pos[:3]
            last_xyz = printer_state.get("_last_xyz", current_xyz)
            printer_state["is_moving"] = any(abs(c - l) > 0.5 for c, l in zip(current_xyz, last_xyz))
            printer_state["_last_xyz"] = current_xyz

            try:
                h_url = f"{self._cached_url}/server/history/totals"
                h_r = http_client.get(h_url, timeout=1)
                if h_r.status_code == 200:
                    totals = h_r.json().get("result", {}).get("job_totals", {})
                    printer_state["stats"]["total_time"] = totals.get("total_time", 0)
                    printer_state["stats"]["total_filament"] = totals.get("total_filament_used", 0)
                    printer_state["stats"]["total_jobs"] = totals.get("total_jobs", 0)
            except Exception:
                pass

            state["status"]["printer"] = True
        except Exception as exc:
            logger.warning("op=fetch_printer_data status=parse_failed reason=%s", exc)