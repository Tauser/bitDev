import copy
import json
import os
import shutil
import tempfile
from typing import Any, Optional


class ConfigWriteError(RuntimeError):
    pass


def _deepcopy_default(default: Any) -> Any:
    return copy.deepcopy(default)


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_config(path: str, default: Any = None, backup_path: Optional[str] = None, logger=None) -> Any:
    backup = backup_path or f"{path}.bak"

    try:
        return _read_json(path)
    except FileNotFoundError:
        return _deepcopy_default(default)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if logger is not None:
            logger.warning("op=config_read status=failed path=%s reason=%s", path, exc)

    try:
        if os.path.exists(backup):
            data = _read_json(backup)
            if logger is not None:
                logger.warning("op=config_read status=using_backup path=%s backup=%s", path, backup)
            return data
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if logger is not None:
            logger.warning("op=config_read_backup status=failed backup=%s reason=%s", backup, exc)

    return _deepcopy_default(default)


def _fsync_parent_dir(path: str) -> None:
    directory = os.path.dirname(path) or "."
    flags = getattr(os, "O_DIRECTORY", None)
    if flags is None:
        return

    dir_fd = None
    try:
        dir_fd = os.open(directory, os.O_RDONLY | flags)
        os.fsync(dir_fd)
    except OSError:
        return
    finally:
        if dir_fd is not None:
            os.close(dir_fd)


def write_config(
    path: str,
    config: Any,
    backup_path: Optional[str] = None,
    logger=None,
    file_mode: Optional[int] = None,
) -> None:
    backup = backup_path or f"{path}.bak"
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())

        if os.path.exists(path):
            shutil.copy2(path, backup)
            if file_mode is not None:
                os.chmod(backup, file_mode)

        os.replace(tmp_path, path)

        if file_mode is not None:
            os.chmod(path, file_mode)

        _fsync_parent_dir(path)
    except Exception as exc:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass

        if logger is not None:
            logger.error("op=config_write status=failed path=%s reason=%s", path, exc)
        raise ConfigWriteError(f"Falha ao persistir config em {path}") from exc
