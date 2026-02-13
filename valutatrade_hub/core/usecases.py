from __future__ import annotations

from datetime import datetime

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import (
    generate_salt,
    hash_password,
    normalize_currency_code,
    resolve_rate_from_cache,
    resolve_rate_from_stub,
    upsert_rate,
    validate_amount,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import setup_logging


class TradingPlatformService:
    def __init__(self) -> None:
        setup_logging()
        self._settings = SettingsLoader()
        self._db = DatabaseManager()
        self._current_user: User | None = None
        self._action_context: dict[str, object] = {}

    @property
    def current_user(self) -> User | None:
        return self._current_user

    @log_action("REGISTER")
    def register(self, username: str, password: str) -> str:
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя не может быть пустым")
        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        users_data = self._db.get_users()
        normalized_username = username.strip()

        if any(item["username"] == normalized_username for item in users_data):
            raise ValueError(f"Имя пользователя '{normalized_username}' уже занято")

        next_user_id = max((int(item["user_id"]) for item in users_data), default=0) + 1
        salt = generate_salt()
        hashed_password = hash_password(password, salt)

        user = User(
            user_id=next_user_id,
            username=normalized_username,
            hashed_password=hashed_password,
            salt=salt,
            registration_date=datetime.now(),
        )

        users_data.append(user.to_dict())
        self._db.save_users(users_data)

        portfolios_data = self._db.get_portfolios()
        portfolios_data.append(Portfolio(user_id=next_user_id).to_dict())
        self._db.save_portfolios(portfolios_data)

        self._action_context = {
            "currency_code": "-",
            "amount": "-",
            "base": "-",
            "details": f"registered_user_id={next_user_id}",
        }
        return (
            f"Пользователь '{normalized_username}' "
            f"зарегистрирован (id={next_user_id}). "
            f"Войдите: login --username {normalized_username} --password ****"
        )

    @log_action("LOGIN")
    def login(self, username: str, password: str) -> str:
        users_data = self._db.get_users()
        payload = next(
            (item for item in users_data if item["username"] == username),
            None,
        )

        if payload is None:
            raise ValueError(f"Пользователь '{username}' не найден")

        user = User.from_dict(payload)
        if not user.verify_password(password):
            raise ValueError("Неверный пароль")

        self._current_user = user
        self._action_context = {
            "currency_code": "-",
            "amount": "-",
            "base": "-",
        }
        return f"Вы вошли как '{user.username}'"

    def show_portfolio(self, base_currency: str = "USD") -> str:
        user = self._require_login()
        base_currency = normalize_currency_code(base_currency)
        get_currency(base_currency)

        portfolio = self._load_portfolio(user)
        wallets = portfolio.wallets
        if not wallets:
            return f"Портфель пользователя '{user.username}' пуст"

        lines = [f"Портфель пользователя '{user.username}' (база: {base_currency}):"]
        total = 0.0

        for code in sorted(wallets.keys()):
            wallet = wallets[code]
            rate, _updated_at = self._resolve_rate(code, base_currency)
            converted = wallet.balance * rate
            total += converted
            lines.append(
                f"- {code}: {wallet.balance:.4f}  -> "
                f"{converted:,.2f} {base_currency}"
            )

        lines.append("---------------------------------")
        lines.append(f"ИТОГО: {total:,.2f} {base_currency}")
        return "\n".join(lines)

    @log_action("BUY", verbose=True)
    def buy(self, currency: str, amount: float) -> str:
        user = self._require_login()
        amount = validate_amount(amount)
        currency_obj = get_currency(currency)

        portfolio = self._load_portfolio(user)
        wallet = portfolio.get_wallet(currency_obj.code)
        if wallet is None:
            wallet = portfolio.add_currency(currency_obj.code)

        usd_wallet = portfolio.get_wallet("USD")
        if usd_wallet is None:
            usd_wallet = portfolio.add_currency("USD")

        rate, _updated_at = self._resolve_rate(currency_obj.code, "USD")
        cost_usd = amount * rate

        usd_before = usd_wallet.balance
        asset_before = wallet.balance

        usd_wallet.withdraw(cost_usd)
        wallet.deposit(amount)

        self._save_portfolio(portfolio)
        self._action_context = {
            "currency_code": currency_obj.code,
            "amount": amount,
            "rate": rate,
            "base": "USD",
            "details": (
                f"usd:{usd_before:.4f}->{usd_wallet.balance:.4f};"
                f"asset:{asset_before:.4f}->{wallet.balance:.4f}"
            ),
        }

        return (
            f"Покупка выполнена: {amount:.4f} {currency_obj.code} "
            f"по курсу {rate:.2f} USD/{currency_obj.code}\n"
            "Изменения в портфеле:\n"
            f"- {currency_obj.code}: было {asset_before:.4f} -> "
            f"стало {wallet.balance:.4f}\n"
            f"Оценочная стоимость покупки: {cost_usd:,.2f} USD"
        )

    @log_action("SELL", verbose=True)
    def sell(self, currency: str, amount: float) -> str:
        user = self._require_login()
        amount = validate_amount(amount)
        currency_obj = get_currency(currency)

        portfolio = self._load_portfolio(user)
        wallet = portfolio.get_wallet(currency_obj.code)
        if wallet is None:
            raise ValueError(
                f"У вас нет кошелька '{currency_obj.code}'. "
                "Она создаётся автоматически при первой покупке."
            )

        usd_wallet = portfolio.get_wallet("USD")
        if usd_wallet is None:
            usd_wallet = portfolio.add_currency("USD")

        asset_before = wallet.balance
        usd_before = usd_wallet.balance

        wallet.withdraw(amount)
        rate, _updated_at = self._resolve_rate(currency_obj.code, "USD")
        proceeds = amount * rate
        usd_wallet.deposit(proceeds)

        self._save_portfolio(portfolio)
        self._action_context = {
            "currency_code": currency_obj.code,
            "amount": amount,
            "rate": rate,
            "base": "USD",
            "details": (
                f"asset:{asset_before:.4f}->{wallet.balance:.4f};"
                f"usd:{usd_before:.4f}->{usd_wallet.balance:.4f}"
            ),
        }

        return (
            f"Продажа выполнена: {amount:.4f} {currency_obj.code} "
            f"по курсу {rate:.2f} USD/{currency_obj.code}\n"
            "Изменения в портфеле:\n"
            f"- {currency_obj.code}: было {asset_before:.4f} -> "
            f"стало {wallet.balance:.4f}\n"
            f"Оценочная выручка: {proceeds:,.2f} USD"
        )

    def get_rate(self, from_code: str, to_code: str) -> str:
        from_currency = get_currency(from_code)
        to_currency = get_currency(to_code)

        rate, updated_at = self._resolve_rate(from_currency.code, to_currency.code)
        reverse = 0.0 if rate == 0 else 1.0 / rate

        return (
            f"Курс {from_currency.code}->{to_currency.code}: {rate:.8f} "
            f"(обновлено: {updated_at})\n"
            f"Обратный курс {to_currency.code}->{from_currency.code}: {reverse:.8f}"
        )

    def _require_login(self) -> User:
        if self._current_user is None:
            raise ValueError("Сначала выполните login")
        return self._current_user

    def _load_portfolio(self, user: User) -> Portfolio:
        portfolios = self._db.get_portfolios()
        payload = next(
            (item for item in portfolios if int(item["user_id"]) == user.user_id),
            None,
        )

        if payload is None:
            portfolio = Portfolio(user_id=user.user_id, user=user)
            portfolios.append(portfolio.to_dict())
            self._db.save_portfolios(portfolios)
            return portfolio

        return Portfolio.from_dict(payload, user=user)

    def _save_portfolio(self, portfolio: Portfolio) -> None:
        portfolios = self._db.get_portfolios()
        replaced = False

        for idx, item in enumerate(portfolios):
            if int(item["user_id"]) == portfolio.user_id:
                portfolios[idx] = portfolio.to_dict()
                replaced = True
                break

        if not replaced:
            portfolios.append(portfolio.to_dict())

        self._db.save_portfolios(portfolios)

    def _resolve_rate(self, from_code: str, to_code: str) -> tuple[float, str]:
        from_code = normalize_currency_code(from_code)
        to_code = normalize_currency_code(to_code)

        ttl_seconds = int(self._settings.get("RATES_TTL_SECONDS", 300))
        rates_payload = self._db.get_rates()

        cached = resolve_rate_from_cache(rates_payload, from_code, to_code, ttl_seconds)
        if cached is not None:
            return cached

        try:
            fresh_rate = resolve_rate_from_stub(from_code, to_code)
        except ApiRequestError:
            raise
        except Exception as exc:
            raise ApiRequestError(str(exc)) from exc

        updated_rates, updated_at = upsert_rate(
            rates_payload,
            from_code,
            to_code,
            fresh_rate,
        )
        self._db.save_rates(updated_rates)
        return fresh_rate, updated_at
