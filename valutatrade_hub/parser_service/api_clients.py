from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    def __init__(self, config: ParserConfig) -> None:
        self.config = config
        self.last_fetch_meta: dict[str, dict[str, Any]] = {}
        self.last_updated_at = datetime.now(timezone.utc).isoformat()

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable data source name."""

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Fetch normalized rates map: {PAIR: rate}."""


class CoinGeckoClient(BaseApiClient):
    @property
    def source_name(self) -> str:
        return "CoinGecko"

    def fetch_rates(self) -> dict[str, float]:
        ids = [
            self.config.crypto_id_map[code]
            for code in self.config.crypto_currencies
        ]
        params = {
            "ids": ",".join(ids),
            "vs_currencies": self.config.base_currency.lower(),
        }

        start = time.perf_counter()
        try:
            response = requests.get(
                self.config.coingecko_url,
                params=params,
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"CoinGecko: {exc}") from exc

        duration_ms = int((time.perf_counter() - start) * 1000)
        payload = response.json()
        updated_at = datetime.now(timezone.utc).isoformat()

        rates: dict[str, float] = {}
        meta: dict[str, dict[str, Any]] = {}

        for code in self.config.crypto_currencies:
            raw_id = self.config.crypto_id_map[code]
            raw_item = payload.get(raw_id)
            if not isinstance(raw_item, dict):
                continue
            raw_rate = raw_item.get(self.config.base_currency.lower())
            if not isinstance(raw_rate, (int, float)):
                continue

            pair = f"{code}_{self.config.base_currency}"
            rates[pair] = float(raw_rate)
            meta[pair] = {
                "raw_id": raw_id,
                "request_ms": duration_ms,
                "status_code": response.status_code,
                "etag": response.headers.get("ETag", ""),
            }

        self.last_fetch_meta = meta
        self.last_updated_at = updated_at
        return rates


class ExchangeRateApiClient(BaseApiClient):
    @property
    def source_name(self) -> str:
        return "ExchangeRate-API"

    def fetch_rates(self) -> dict[str, float]:
        if not self.config.exchangerate_api_key:
            raise ApiRequestError("ExchangeRate-API: отсутствует EXCHANGERATE_API_KEY")

        base = self.config.base_currency
        url = (
            f"{self.config.exchangerate_api_url}/"
            f"{self.config.exchangerate_api_key}/latest/{base}"
        )

        start = time.perf_counter()
        try:
            response = requests.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"ExchangeRate-API: {exc}") from exc

        duration_ms = int((time.perf_counter() - start) * 1000)
        payload = response.json()

        if payload.get("result") != "success":
            reason = payload.get("error-type", "unknown API error")
            raise ApiRequestError(f"ExchangeRate-API: {reason}")

        timestamp = payload.get("time_last_update_utc")
        updated_at = datetime.now(timezone.utc).isoformat()
        if isinstance(timestamp, str) and timestamp:
            updated_at = updated_at

        raw_rates = payload.get("rates", {})
        rates: dict[str, float] = {}
        meta: dict[str, dict[str, Any]] = {}

        for code in self.config.fiat_currencies:
            raw_rate = raw_rates.get(code)
            if not isinstance(raw_rate, (int, float)):
                continue

            # API gives BASE->CODE, convert to CODE->BASE for uniformity.
            if float(raw_rate) == 0:
                continue
            pair = f"{code}_{base}"
            rates[pair] = 1.0 / float(raw_rate)
            meta[pair] = {
                "raw_id": code,
                "request_ms": duration_ms,
                "status_code": response.status_code,
                "etag": response.headers.get("ETag", ""),
            }

        self.last_fetch_meta = meta
        self.last_updated_at = updated_at
        return rates
