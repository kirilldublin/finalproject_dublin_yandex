from __future__ import annotations

import shlex

from valutatrade_hub.core.currencies import list_supported_codes
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import TradingPlatformService
from valutatrade_hub.logging_config import setup_parser_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import ParserStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def _parse_named_args(tokens: list[str]) -> dict[str, str]:
    args: dict[str, str] = {}
    i = 0

    while i < len(tokens):
        token = tokens[i]
        if not token.startswith("--"):
            raise ValueError(f"Неожиданный аргумент: {token}")

        key = token[2:]
        if not key:
            raise ValueError("Пустое имя аргумента")
        if i + 1 >= len(tokens):
            raise ValueError(f"Для аргумента '{token}' не указано значение")

        args[key] = tokens[i + 1]
        i += 2

    return args


def print_help() -> None:
    print(
        "\n".join(
            [
                "Команды:",
                "  register --username <str> --password <str>",
                "  login --username <str> --password <str>",
                "  show-portfolio [--base <str>]",
                "  buy --currency <str> --amount <float>",
                "  sell --currency <str> --amount <float>",
                "  get-rate --from <str> --to <str>",
                "  update-rates [--source <coingecko|exchangerate>]",
                "  show-rates [--currency <str>] [--top <int>] [--base <str>]",
                "  help",
                "  exit",
                f"Поддерживаемые валюты: {', '.join(list_supported_codes())}",
            ]
        )
    )


def _build_parser_updater() -> tuple[RatesUpdater, ParserStorage]:
    config = ParserConfig.from_settings()
    storage = ParserStorage(config)
    logger = setup_parser_logging()
    clients = [CoinGeckoClient(config), ExchangeRateApiClient(config)]
    return RatesUpdater(clients=clients, storage=storage, logger=logger), storage


def _show_rates_from_cache(
    storage: ParserStorage,
    currency: str | None,
    top: int | None,
    base: str | None,
) -> str:
    payload = storage.read_rates_cache()
    pairs = payload.get("pairs", {})
    if not isinstance(pairs, dict) or not pairs:
        raise ValueError(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', чтобы загрузить данные."
        )

    rows: list[tuple[str, float, str]] = []
    for pair, data in pairs.items():
        if not isinstance(data, dict):
            continue
        rate = data.get("rate")
        updated_at = str(data.get("updated_at", ""))
        if not isinstance(rate, (int, float)):
            continue

        from_code, to_code = pair.split("_", 1)
        if currency and currency.upper() not in {from_code, to_code}:
            continue
        if base and to_code != base.upper():
            continue
        rows.append((pair, float(rate), updated_at))

    if not rows:
        target = currency or base or "указанных фильтров"
        raise ValueError(f"Курс для '{target}' не найден в кеше.")

    if top is not None:
        rows = sorted(rows, key=lambda item: item[1], reverse=True)[:top]
    else:
        rows = sorted(rows, key=lambda item: item[0])

    lines = [f"Rates from cache (updated at {payload.get('last_refresh')}):"]
    for pair, rate, updated_at in rows:
        lines.append(f"- {pair}: {rate:.8f} (updated: {updated_at})")
    return "\n".join(lines)


def run_cli() -> None:
    service = TradingPlatformService()
    print("ValutaTrade Hub CLI. Введите 'help' для списка команд.")

    while True:
        raw = input("> ").strip()
        if not raw:
            continue

        try:
            parts = shlex.split(raw)
        except ValueError as exc:
            print(f"Ошибка парсинга команды: {exc}")
            continue

        command = parts[0].lower()
        tokens = parts[1:]

        if command in {"exit", "quit"}:
            print("Выход.")
            break

        if command == "help":
            print_help()
            continue

        try:
            options = _parse_named_args(tokens)

            if command == "register":
                print(service.register(options["username"], options["password"]))
            elif command == "login":
                print(service.login(options["username"], options["password"]))
            elif command == "show-portfolio":
                print(service.show_portfolio(options.get("base", "USD")))
            elif command == "buy":
                print(service.buy(options["currency"], float(options["amount"])))
            elif command == "sell":
                print(service.sell(options["currency"], float(options["amount"])))
            elif command == "get-rate":
                print(service.get_rate(options["from"], options["to"]))
            elif command == "update-rates":
                updater, _storage = _build_parser_updater()
                source = options.get("source")
                result = updater.run_update(source=source)
                if result["errors"]:
                    print(
                        "Update completed with errors. "
                        "Check logs/parser.log for details."
                    )
                else:
                    print(
                        "Update successful. "
                        f"Total rates updated: {result['updated_count']}. "
                        f"Last refresh: {result['last_refresh']}"
                    )
            elif command == "show-rates":
                _updater, storage = _build_parser_updater()
                currency = options.get("currency")
                base = options.get("base")
                top = int(options["top"]) if "top" in options else None
                print(_show_rates_from_cache(storage, currency, top, base))
            else:
                print("Неизвестная команда. Введите 'help'.")
        except KeyError as exc:
            print(f"Отсутствует обязательный аргумент: --{exc.args[0]}")
        except InsufficientFundsError as exc:
            print(str(exc))
        except CurrencyNotFoundError as exc:
            codes = ", ".join(list_supported_codes())
            print(f"{exc}. Поддерживаемые коды: {codes}")
        except ApiRequestError as exc:
            print(f"{exc}. Повторите позже или проверьте сеть/Parser Service.")
        except ValueError as exc:
            print(str(exc))
