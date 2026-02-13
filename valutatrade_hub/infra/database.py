from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._settings = SettingsLoader()
        self._ensure_storage()
        self._initialized = True

    def _ensure_storage(self) -> None:
        data_dir = self._settings.resolve_path("DATA_DIR")
        data_dir.mkdir(parents=True, exist_ok=True)

        defaults: list[tuple[Path, Any]] = [
            (self._settings.resolve_path("USERS_FILE"), []),
            (self._settings.resolve_path("PORTFOLIOS_FILE"), []),
            (self._settings.resolve_path("RATES_FILE"), {}),
        ]

        for path, payload in defaults:
            if not path.exists():
                self._write_json(path, payload)

    def _read_json(self, path: Path, default: Any) -> Any:
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _write_json(self, path: Path, payload: Any) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def get_users(self) -> list[dict[str, Any]]:
        path = self._settings.resolve_path("USERS_FILE")
        return self._read_json(path, default=[])

    def save_users(self, users: list[dict[str, Any]]) -> None:
        path = self._settings.resolve_path("USERS_FILE")
        self._write_json(path, users)

    def get_portfolios(self) -> list[dict[str, Any]]:
        path = self._settings.resolve_path("PORTFOLIOS_FILE")
        return self._read_json(path, default=[])

    def save_portfolios(self, portfolios: list[dict[str, Any]]) -> None:
        path = self._settings.resolve_path("PORTFOLIOS_FILE")
        self._write_json(path, portfolios)

    def get_rates(self) -> dict[str, Any]:
        path = self._settings.resolve_path("RATES_FILE")
        return self._read_json(path, default={})

    def save_rates(self, rates: dict[str, Any]) -> None:
        path = self._settings.resolve_path("RATES_FILE")
        self._write_json(path, rates)
