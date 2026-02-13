from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError

_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z0-9]{2,5}$")


def normalize_currency_code(currency_code: str) -> str:
    if not isinstance(currency_code, str):
        raise ValueError("Код валюты должен быть строкой")
    normalized = currency_code.strip().upper()
    if not _CURRENCY_CODE_PATTERN.match(normalized):
        raise ValueError("Код валюты должен быть в формате 2-5 символов A-Z0-9")
    return normalized


def validate_amount(amount: Any) -> float:
    try:
        numeric = float(amount)
    except (TypeError, ValueError) as exc:
        raise ValueError("'amount' должен быть положительным числом") from exc

    if numeric <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return numeric


def hash_password(password: str, salt: str) -> str:
    payload = f"{password}{salt}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def generate_salt() -> str:
    return secrets.token_hex(8)


def is_rate_fresh(updated_at: str, ttl_seconds: int) -> bool:
    try:
        normalized = updated_at.replace("Z", "+00:00")
        updated = datetime.fromisoformat(normalized)
    except ValueError:
        return False

    if updated.tzinfo is None:
        now = datetime.now()
    else:
        now = datetime.now(updated.tzinfo)
    return now - updated <= timedelta(seconds=ttl_seconds)


def resolve_rate_from_cache(
    rates_payload: dict[str, Any],
    from_code: str,
    to_code: str,
    ttl_seconds: int,
) -> tuple[float, str] | None:
    pairs = rates_payload.get("pairs", rates_payload)
    if not isinstance(pairs, dict):
        return None

    if from_code == to_code:
        now = datetime.now().isoformat(timespec="seconds")
        return 1.0, now

    pair = f"{from_code}_{to_code}"
    reverse_pair = f"{to_code}_{from_code}"

    direct_entry = pairs.get(pair)
    if isinstance(direct_entry, dict):
        updated_at = str(direct_entry.get("updated_at", ""))
        if is_rate_fresh(updated_at, ttl_seconds):
            return float(direct_entry["rate"]), updated_at

    reverse_entry = pairs.get(reverse_pair)
    if isinstance(reverse_entry, dict):
        updated_at = str(reverse_entry.get("updated_at", ""))
        reverse_rate = float(reverse_entry.get("rate", 0.0))
        if reverse_rate > 0 and is_rate_fresh(updated_at, ttl_seconds):
            return 1.0 / reverse_rate, updated_at

    return None


def resolve_rate_from_stub(from_code: str, to_code: str) -> float:
    if from_code == to_code:
        return 1.0

    usd_rates = {
        "USD": 1.0,
        "EUR": 1.0786,
        "BTC": 59337.21,
        "RUB": 0.01016,
        "ETH": 3720.0,
    }

    if from_code not in usd_rates or to_code not in usd_rates:
        raise ApiRequestError(f"курс {from_code}->{to_code} не найден")

    # Convert via USD bridge.
    from_to_usd = usd_rates[from_code]
    to_to_usd = usd_rates[to_code]
    return from_to_usd / to_to_usd


def upsert_rate(
    rates_payload: dict[str, Any],
    from_code: str,
    to_code: str,
    rate: float,
    source: str = "LocalStub",
) -> tuple[dict[str, Any], str]:
    now = datetime.now().isoformat(timespec="seconds")
    key = f"{from_code}_{to_code}"
    pairs = rates_payload.get("pairs")
    if not isinstance(pairs, dict):
        pairs = {}

    pairs[key] = {
        "rate": rate,
        "updated_at": now,
        "source": source,
    }
    rates_payload["pairs"] = pairs
    rates_payload["last_refresh"] = now
    return rates_payload, now
