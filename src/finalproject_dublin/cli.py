from __future__ import annotations

import json
import shlex
import time
from functools import wraps
from pathlib import Path

from prettytable import PrettyTable

DATA_FILE = Path("wallet.json")


def timed(func):
    """Decorator that prints command execution time."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        print(f"[timing] {func.__name__}: {duration:.2f} ms")
        return result

    return wrapper


def confirm_action(func):
    """Decorator for commands that modify wallet state."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        answer = input(f"Подтвердить {func.__name__}? [y/N]: ").strip().lower()
        if answer != "y":
            print("Операция отменена.")
            return None
        return func(self, *args, **kwargs)

    return wrapper


def make_rate_cache():
    """Closure-based cache for exchange rates."""

    cache: dict[tuple[str, str], float] = {}

    def get_rate(from_currency: str, to_currency: str) -> float:
        key = (from_currency.upper(), to_currency.upper())
        if key not in cache:
            # Temporary static rates for initial project stage.
            static_rates = {
                ("USD", "EUR"): 0.93,
                ("EUR", "USD"): 1.07,
                ("USD", "RUB"): 90.0,
                ("RUB", "USD"): 1 / 90.0,
            }
            if key not in static_rates:
                raise ValueError(f"Курс для {key[0]}->{key[1]} не найден")
            cache[key] = static_rates[key]
        return cache[key]

    return get_rate


class CurrencyWallet:
    def __init__(self, data_file: Path = DATA_FILE):
        self.data_file = data_file
        self.balances: dict[str, float] = {}
        self._rate_provider = make_rate_cache()
        self.load()

    def load(self) -> None:
        if not self.data_file.exists():
            self.balances = {"USD": 0.0}
            self.save()
            return
        try:
            with self.data_file.open("r", encoding="utf-8") as f:
                self.balances = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Ошибка загрузки данных: {exc}")
            self.balances = {"USD": 0.0}

    def save(self) -> None:
        with self.data_file.open("w", encoding="utf-8") as f:
            json.dump(self.balances, f, ensure_ascii=False, indent=2)

    def show_balances(self) -> None:
        table = PrettyTable()
        table.field_names = ["Currency", "Amount"]
        for currency, amount in sorted(self.balances.items()):
            table.add_row([currency, f"{amount:.2f}"])
        print(table)

    @confirm_action
    def deposit(self, currency: str, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть больше 0")
        currency = currency.upper()
        self.balances[currency] = self.balances.get(currency, 0.0) + amount
        self.save()
        print(f"Пополнение: +{amount:.2f} {currency}")

    @confirm_action
    def withdraw(self, currency: str, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Сумма списания должна быть больше 0")
        currency = currency.upper()
        if self.balances.get(currency, 0.0) < amount:
            raise ValueError("Недостаточно средств")
        self.balances[currency] -= amount
        self.save()
        print(f"Списание: -{amount:.2f} {currency}")

    @confirm_action
    def convert(self, from_currency: str, to_currency: str, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Сумма конвертации должна быть больше 0")
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        if self.balances.get(from_currency, 0.0) < amount:
            raise ValueError("Недостаточно средств для конвертации")

        rate = self._rate_provider(from_currency, to_currency)
        converted = amount * rate

        self.balances[from_currency] -= amount
        self.balances[to_currency] = self.balances.get(to_currency, 0.0) + converted
        self.save()
        print(
            f"Конвертация: {amount:.2f} {from_currency} -> "
            f"{converted:.2f} {to_currency}"
        )


@timed
def process_command(wallet: CurrencyWallet, raw_command: str) -> bool:
    try:
        parts = shlex.split(raw_command)
    except ValueError as exc:
        print(f"Ошибка парсинга команды: {exc}")
        return True

    if not parts:
        return True

    command = parts[0].lower()

    try:
        if command in {"exit", "quit"}:
            return False
        if command == "help":
            print_help()
        elif command == "balance":
            wallet.show_balances()
        elif command == "deposit" and len(parts) == 3:
            wallet.deposit(parts[1], float(parts[2]))
        elif command == "withdraw" and len(parts) == 3:
            wallet.withdraw(parts[1], float(parts[2]))
        elif command == "convert" and len(parts) == 4:
            wallet.convert(parts[1], parts[2], float(parts[3]))
        else:
            print("Неизвестная команда или неверное количество аргументов. help")
    except ValueError as exc:
        print(f"Ошибка: {exc}")

    return True


def print_help() -> None:
    print(
        "\n".join(
            [
                "Доступные команды:",
                "  help",
                "  balance",
                "  deposit <currency> <amount>",
                "  withdraw <currency> <amount>",
                "  convert <from_currency> <to_currency> <amount>",
                "  exit",
            ]
        )
    )


def main() -> None:
    wallet = CurrencyWallet()
    print("Currency wallet started. Type 'help' for command list.")

    running = True
    while running:
        raw = input("> ").strip()
        running = process_command(wallet, raw)


if __name__ == "__main__":
    main()
