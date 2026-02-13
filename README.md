# finalproject_dublin

Платформа для отслеживания и симуляции торговли валютами (CLI).

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

## CLI

```text
register --username alice --password 1234
login --username alice --password 1234
get-rate --from BTC --to USD
show-portfolio
buy --currency BTC --amount 0.01
sell --currency BTC --amount 0.005
show-portfolio --base USD
update-rates
show-rates --top 2
exit
```
