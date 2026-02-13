from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


class SettingsLoader:
    """Singleton via __new__: simple and explicit for one shared config instance."""

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._base_dir = Path(__file__).resolve().parents[2]
        self._config: dict[str, Any] = {}
        self.reload()
        self._initialized = True

    def reload(self) -> None:
        defaults = {
            "DATA_DIR": "data",
            "USERS_FILE": "data/users.json",
            "PORTFOLIOS_FILE": "data/portfolios.json",
            "RATES_FILE": "data/rates.json",
            "EXCHANGE_HISTORY_FILE": "data/exchange_rates.json",
            "RATES_TTL_SECONDS": 300,
            "DEFAULT_BASE_CURRENCY": "USD",
            "LOG_FILE": "logs/actions.log",
            "PARSER_LOG_FILE": "logs/parser.log",
            "LOG_LEVEL": "INFO",
            "LOG_FORMAT": "text",
            "LOG_MAX_BYTES": 1_048_576,
            "LOG_BACKUP_COUNT": 3,
            "REQUEST_TIMEOUT": 10,
        }

        config_path = self._base_dir / "pyproject.toml"
        tool_config: dict[str, Any] = {}

        if config_path.exists():
            with config_path.open("rb") as file:
                parsed = tomllib.load(file)
            tool_config = parsed.get("tool", {}).get("valutatrade", {})

        merged = defaults.copy()
        merged.update(tool_config)
        self._config = merged

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def resolve_path(self, key: str) -> Path:
        value = self.get(key)
        if value is None:
            raise KeyError(f"Unknown settings key: {key}")
        path = Path(str(value))
        if not path.is_absolute():
            path = self._base_dir / path
        return path
