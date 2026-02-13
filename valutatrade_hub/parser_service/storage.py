from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from valutatrade_hub.parser_service.config import ParserConfig


class ParserStorage:
    def __init__(self, config: ParserConfig) -> None:
        self._config = config
        self._ensure_files()

    def _ensure_files(self) -> None:
        self._config.rates_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._config.history_file_path.parent.mkdir(parents=True, exist_ok=True)

        if not self._config.rates_file_path.exists():
            self.atomic_write_json(
                self._config.rates_file_path,
                {"pairs": {}, "last_refresh": None},
            )
        if not self._config.history_file_path.exists():
            self.atomic_write_json(self._config.history_file_path, [])

    def read_rates_cache(self) -> dict[str, Any]:
        return self._read_json(self._config.rates_file_path, {"pairs": {}})

    def write_rates_cache(
        self,
        updates: dict[str, dict[str, Any]],
        last_refresh: str,
    ) -> int:
        cache = self.read_rates_cache()
        pairs = cache.get("pairs", {})
        if not isinstance(pairs, dict):
            pairs = {}

        updated_count = 0
        for pair, entry in updates.items():
            current = pairs.get(pair)
            if self._should_replace(current, entry):
                pairs[pair] = entry
                updated_count += 1

        cache["pairs"] = pairs
        cache["last_refresh"] = last_refresh
        self.atomic_write_json(self._config.rates_file_path, cache)
        return updated_count

    def append_history(self, records: list[dict[str, Any]]) -> int:
        history = self._read_json(self._config.history_file_path, [])
        if not isinstance(history, list):
            history = []

        existing_ids = {
            str(item.get("id"))
            for item in history
            if isinstance(item, dict)
        }
        added = 0

        for record in records:
            record_id = str(record.get("id", ""))
            if not record_id or record_id in existing_ids:
                continue
            history.append(record)
            existing_ids.add(record_id)
            added += 1

        self.atomic_write_json(self._config.history_file_path, history)
        return added

    def atomic_write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=str(path.parent),
            prefix=f"{path.name}.tmp.",
        ) as temp_file:
            json.dump(payload, temp_file, ensure_ascii=False, indent=2)
            temp_path = Path(temp_file.name)

        temp_path.replace(path)

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    @staticmethod
    def _should_replace(
        current: dict[str, Any] | None,
        incoming: dict[str, Any],
    ) -> bool:
        if current is None:
            return True
        current_updated = str(current.get("updated_at", ""))
        incoming_updated = str(incoming.get("updated_at", ""))
        if not current_updated:
            return True
        if not incoming_updated:
            return False

        try:
            cur_dt = datetime.fromisoformat(current_updated.replace("Z", "+00:00"))
            inc_dt = datetime.fromisoformat(incoming_updated.replace("Z", "+00:00"))
        except ValueError:
            return True

        if cur_dt.tzinfo is None:
            cur_dt = cur_dt.replace(tzinfo=timezone.utc)
        if inc_dt.tzinfo is None:
            inc_dt = inc_dt.replace(tzinfo=timezone.utc)

        return inc_dt >= cur_dt
