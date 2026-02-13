from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.storage import ParserStorage


class RatesUpdater:
    def __init__(
        self,
        clients: list[BaseApiClient],
        storage: ParserStorage,
        logger: logging.Logger,
    ) -> None:
        self._clients = clients
        self._storage = storage
        self._logger = logger

    def run_update(self, source: str | None = None) -> dict[str, Any]:
        started = datetime.now(timezone.utc).isoformat()
        self._logger.info("Starting rates update")

        selected = self._select_clients(source)
        combined_updates: dict[str, dict[str, Any]] = {}
        history_records: list[dict[str, Any]] = []
        errors: list[str] = []

        for client in selected:
            try:
                self._logger.info("Fetching from %s", client.source_name)
                rates = client.fetch_rates()
                for pair, rate in rates.items():
                    entry = {
                        "rate": float(rate),
                        "updated_at": client.last_updated_at,
                        "source": client.source_name,
                    }
                    combined_updates[pair] = entry

                    from_code, to_code = pair.split("_", 1)
                    timestamp = client.last_updated_at
                    record_id = f"{from_code}_{to_code}_{timestamp}"

                    history_records.append(
                        {
                            "id": record_id,
                            "from_currency": from_code,
                            "to_currency": to_code,
                            "rate": float(rate),
                            "timestamp": timestamp,
                            "source": client.source_name,
                            "meta": client.last_fetch_meta.get(pair, {}),
                        }
                    )

                self._logger.info("%s OK (%d rates)", client.source_name, len(rates))
            except ApiRequestError as exc:
                message = f"Failed to fetch from {client.source_name}: {exc}"
                self._logger.error(message)
                errors.append(message)

        updated_count = self._storage.write_rates_cache(combined_updates, started)
        history_added = self._storage.append_history(history_records)

        self._logger.info(
            "Update finished: rates=%d history=%d errors=%d",
            updated_count,
            history_added,
            len(errors),
        )

        return {
            "updated_count": updated_count,
            "history_added": history_added,
            "last_refresh": started,
            "errors": errors,
        }

    def _select_clients(self, source: str | None) -> list[BaseApiClient]:
        if source is None:
            return self._clients

        normalized = source.strip().lower()
        mapping = {
            "coingecko": "CoinGecko",
            "exchangerate": "ExchangeRate-API",
        }
        expected_name = mapping.get(normalized)
        if expected_name is None:
            raise ValueError("--source должен быть 'coingecko' или 'exchangerate'")

        filtered = [
            client
            for client in self._clients
            if client.source_name == expected_name
        ]
        if not filtered:
            raise ValueError(f"Источник '{source}' не настроен")
        return filtered
