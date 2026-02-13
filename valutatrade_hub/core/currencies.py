from __future__ import annotations

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.utils import normalize_currency_code


class Currency(ABC):
    def __init__(self, name: str, code: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Currency name must be a non-empty string")
        self.name = name.strip()
        self.code = normalize_currency_code(code)

    @abstractmethod
    def get_display_info(self) -> str:
        """Return display string for UI and logs."""


class FiatCurrency(Currency):
    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        super().__init__(name=name, code=code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Issuing country must be a non-empty string")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        return (
            f"[FIAT] {self.code} - {self.name} "
            f"(Issuing: {self.issuing_country})"
        )


class CryptoCurrency(Currency):
    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        super().__init__(name=name, code=code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Algorithm must be a non-empty string")
        if not isinstance(market_cap, (int, float)) or float(market_cap) < 0:
            raise ValueError("Market cap must be a non-negative number")
        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        return (
            f"[CRYPTO] {self.code} - {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


_CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.20e11),
}


def get_currency(code: str) -> Currency:
    try:
        normalized = normalize_currency_code(code)
    except ValueError as exc:
        raise CurrencyNotFoundError(str(code)) from exc
    currency = _CURRENCY_REGISTRY.get(normalized)
    if currency is None:
        raise CurrencyNotFoundError(normalized)
    return currency


def list_supported_codes() -> list[str]:
    return sorted(_CURRENCY_REGISTRY.keys())
