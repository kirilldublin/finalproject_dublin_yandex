from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


@dataclass
class ParserConfig:
    exchangerate_api_key: str = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY", "")
    )
    coingecko_url: str = "https://api.coingecko.com/api/v3/simple/price"
    exchangerate_api_url: str = "https://v6.exchangerate-api.com/v6"

    base_currency: str = "USD"
    fiat_currencies: tuple[str, ...] = ("EUR", "GBP", "RUB")
    crypto_currencies: tuple[str, ...] = ("BTC", "ETH", "SOL")
    crypto_id_map: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    request_timeout: int = 10
    rates_file_path: Path = Path("data/rates.json")
    history_file_path: Path = Path("data/exchange_rates.json")

    @classmethod
    def from_settings(cls) -> "ParserConfig":
        settings = SettingsLoader()
        return cls(
            exchangerate_api_key=os.getenv("EXCHANGERATE_API_KEY", ""),
            base_currency=str(settings.get("DEFAULT_BASE_CURRENCY", "USD")),
            request_timeout=int(settings.get("REQUEST_TIMEOUT", 10)),
            rates_file_path=settings.resolve_path("RATES_FILE"),
            history_file_path=settings.resolve_path("EXCHANGE_HISTORY_FILE"),
        )
