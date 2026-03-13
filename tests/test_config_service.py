import json
from pathlib import Path

import pytest

from services.config_service import ConfigWriteError, read_config, write_config


def test_atomic_write_and_backup_roundtrip(tmp_path: Path):
    config_path = tmp_path / "user_config.json"
    first = {"brilho": 70, "secundarias": ["ETHUSDT"]}
    second = {"brilho": 20, "secundarias": ["XRPUSDT"]}

    write_config(str(config_path), first)
    assert json.loads(config_path.read_text(encoding="utf-8")) == first
    assert not config_path.with_suffix(".json.bak").exists()

    write_config(str(config_path), second)

    backup_path = Path(f"{config_path}.bak")
    assert backup_path.exists()
    assert json.loads(backup_path.read_text(encoding="utf-8")) == first
    assert read_config(str(config_path), default=None) == second


def test_write_failure_does_not_corrupt_original(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "user_config.json"
    original = {"brilho": 55}
    write_config(str(config_path), original)

    def broken_dump(obj, handle, indent=2):
        handle.write('{"incompleto":')
        raise RuntimeError("falha simulada")

    monkeypatch.setattr("services.config_service.json.dump", broken_dump)

    with pytest.raises(ConfigWriteError):
        write_config(str(config_path), {"brilho": 99})

    assert json.loads(config_path.read_text(encoding="utf-8")) == original


def test_read_falls_back_to_backup_when_primary_is_corrupted(tmp_path: Path):
    config_path = tmp_path / "user_config.json"
    backup = Path(f"{config_path}.bak")
    valid = {"cidade": "Sao_Paulo", "brilho": 80}

    backup.write_text(json.dumps(valid), encoding="utf-8")
    config_path.write_text('{"cidade": ', encoding="utf-8")

    loaded = read_config(str(config_path), default={"cidade": "fallback"})
    assert loaded == valid


def test_replace_failure_preserves_previous_file(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "user_config.json"
    previous = {"modo_noturno": False}
    write_config(str(config_path), previous)

    def fail_replace(src, dst):
        raise OSError("falha no replace")

    monkeypatch.setattr("services.config_service.os.replace", fail_replace)

    with pytest.raises(ConfigWriteError):
        write_config(str(config_path), {"modo_noturno": True})

    assert json.loads(config_path.read_text(encoding="utf-8")) == previous

    tmp_candidates = list(tmp_path.glob(".user_config.json.*.tmp"))
    assert not tmp_candidates
