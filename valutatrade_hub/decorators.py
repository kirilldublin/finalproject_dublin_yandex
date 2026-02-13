from __future__ import annotations

import inspect
import logging
from datetime import datetime
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger("valutatrade.actions")


def log_action(action: str, verbose: bool = False) -> Callable:
    def decorator(func: Callable) -> Callable:
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()

            service = bound.arguments.get("self")
            if service is not None:
                setattr(service, "_action_context", {})

            user = getattr(service, "current_user", None) if service else None
            username = getattr(user, "username", "-") if user else "-"
            user_id = getattr(user, "user_id", "-") if user else "-"

            timestamp = datetime.now().isoformat(timespec="seconds")
            payload = {
                "timestamp": timestamp,
                "action": action,
                "username": username,
                "user_id": user_id,
                "currency_code": bound.arguments.get("currency", "-"),
                "amount": bound.arguments.get("amount", "-"),
                "rate": "-",
                "base": "-",
            }

            try:
                result = func(*args, **kwargs)
                context = getattr(service, "_action_context", {}) if service else {}
                payload.update(context)
                payload["result"] = "OK"
                payload["error_type"] = "-"
                payload["error_message"] = "-"

                message = _format_log_message(payload, verbose)
                logger.info(message)
                return result
            except Exception as exc:
                context = getattr(service, "_action_context", {}) if service else {}
                payload.update(context)
                payload["result"] = "ERROR"
                payload["error_type"] = exc.__class__.__name__
                payload["error_message"] = str(exc)
                message = _format_log_message(payload, verbose)
                logger.error(message)
                raise

        return wrapper

    return decorator


def _format_log_message(payload: dict[str, Any], verbose: bool) -> str:
    amount = payload.get("amount")
    amount_repr = f"{float(amount):.4f}" if isinstance(amount, (int, float)) else amount

    rate = payload.get("rate")
    rate_repr = f"{float(rate):.8f}" if isinstance(rate, (int, float)) else rate

    message = (
        f"{payload.get('timestamp')} "
        f"action={payload.get('action')} "
        f"user='{payload.get('username')}' "
        f"user_id={payload.get('user_id')} "
        f"currency='{payload.get('currency_code')}' "
        f"amount={amount_repr} "
        f"rate={rate_repr} "
        f"base='{payload.get('base')}' "
        f"result={payload.get('result')} "
        f"error_type={payload.get('error_type')} "
        f"error_message='{payload.get('error_message')}'"
    )

    if verbose and "details" in payload:
        message = f"{message} details='{payload['details']}'"

    return message
