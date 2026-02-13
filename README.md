# finalproject_dublin

Консольная платформа для симуляции торговли валютами:
- регистрация и авторизация пользователей;
- портфель фиатных и криптовалют;
- покупка/продажа активов;
- получение курсов из локального кэша;
- отдельный Parser Service для обновления курсов из внешних API.

## Структура

- `data/users.json` — пользователи
- `data/portfolios.json` — портфели
- `data/rates.json` — кеш курсов
- `valutatrade_hub/core/currencies.py` — иерархия валют (Currency/Fiat/Crypto)
- `valutatrade_hub/core/exceptions.py` — пользовательские исключения
- `valutatrade_hub/core/models.py` — модели `User`, `Wallet`, `Portfolio`
- `valutatrade_hub/core/usecases.py` — бизнес-логика
- `valutatrade_hub/infra/settings.py` — Singleton-конфиг
- `valutatrade_hub/infra/database.py` — Singleton JSON-хранилище
- `valutatrade_hub/decorators.py` — `@log_action`
- `valutatrade_hub/logging_config.py` — ротация и формат логов
- `valutatrade_hub/parser_service/` — сервис парсинга курсов
- `valutatrade_hub/cli/interface.py` — командный интерфейс
- `main.py` — точка входа

## Команды

```bash
make install
make lint
make project
```

## Команды CLI

Core Service
```text
register --username <str> --password <str>
login --username <str> --password <str>
show-portfolio [--base <str>]
buy --currency <str> --amount <float>
sell --currency <str> --amount <float>
get-rate --from <str> --to <str>
```
Parser Service
```text
update-rates [--source <coingecko|exchangerate>]
show-rates [--currency <str>] [--top <int>] [--base <str>]
```

## Demo

![ValutaTrade Hub demo](demo.gif)