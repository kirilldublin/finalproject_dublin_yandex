from __future__ import annotations


class TradingPlatformError(Exception):
    """Base exception for domain-specific errors."""


class InsufficientFundsError(TradingPlatformError):
    def __init__(self, available: float, required: float, code: str) -> None:
        message = (
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(TradingPlatformError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(TradingPlatformError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
