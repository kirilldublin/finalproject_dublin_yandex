from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.utils import normalize_currency_code, validate_amount


class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        self._user_id = int(user_id)
        self._username = ""
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date
        self.username = username

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        payload = f"{password}{salt}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def get_user_info(self) -> dict[str, Any]:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._hashed_password = self._hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        return self._hashed_password == self._hash_password(password, self._salt)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "User":
        return cls(
            user_id=int(payload["user_id"]),
            username=str(payload["username"]),
            hashed_password=str(payload["hashed_password"]),
            salt=str(payload["salt"]),
            registration_date=datetime.fromisoformat(str(payload["registration_date"])),
        )


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        self._currency_code = normalize_currency_code(currency_code)
        self._balance = 0.0
        self.balance = balance

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        value = float(value)
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = value

    def deposit(self, amount: float) -> None:
        self._balance += validate_amount(amount)

    def withdraw(self, amount: float) -> None:
        amount = validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=amount,
                code=self._currency_code,
            )
        self._balance -= amount

    def get_balance_info(self) -> str:
        return f"{self._currency_code}: {self._balance:.4f}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency_code": self._currency_code,
            "balance": self._balance,
        }


class Portfolio:
    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ) -> None:
        self._user_id = int(user_id)
        self._wallets: dict[str, Wallet] = wallets or {}
        self._user = user

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def user(self) -> User | None:
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        return dict(self._wallets)

    def add_currency(self, currency_code: str) -> Wallet:
        normalized = normalize_currency_code(currency_code)
        if normalized in self._wallets:
            raise ValueError(f"Кошелек '{normalized}' уже существует")
        wallet = Wallet(currency_code=normalized)
        self._wallets[normalized] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        normalized = normalize_currency_code(currency_code)
        return self._wallets.get(normalized)

    def get_total_value(
        self,
        base_currency: str,
        rates: dict[str, float],
    ) -> float:
        base = normalize_currency_code(base_currency)
        total = 0.0

        for wallet in self._wallets.values():
            code = wallet.currency_code
            if code == base:
                total += wallet.balance
                continue

            direct_key = f"{code}_{base}"
            reverse_key = f"{base}_{code}"

            if direct_key in rates:
                total += wallet.balance * rates[direct_key]
            elif reverse_key in rates and rates[reverse_key] > 0:
                total += wallet.balance / rates[reverse_key]
            else:
                raise ValueError(f"Неизвестная базовая валюта '{base}'")

        return total

    def to_dict(self) -> dict[str, Any]:
        wallets_payload = {
            code: {
                "currency_code": wallet.currency_code,
                "balance": wallet.balance,
            }
            for code, wallet in self._wallets.items()
        }
        return {
            "user_id": self._user_id,
            "wallets": wallets_payload,
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        user: User | None = None,
    ) -> "Portfolio":
        wallets_raw = payload.get("wallets", {})
        wallets: dict[str, Wallet] = {}

        for code, wallet_data in wallets_raw.items():
            wallets[normalize_currency_code(code)] = Wallet(
                currency_code=code,
                balance=float(wallet_data.get("balance", 0.0)),
            )

        return cls(user_id=int(payload["user_id"]), wallets=wallets, user=user)
