"""
Backend i18n — Accept-Language resolution + lang-aware copy.

Single source of truth for any user-facing string the backend generates:
  • OTP emails (subject + body)
  • Transactional notification copy (title/body)
  • Future: error messages with i18n keys, system-generated activity items

Resolution order for a request's locale:
  1. Explicit `lang` param passed by caller (highest priority)
  2. User record `language` field (persisted via PATCH /account/me from mobile)
  3. `Accept-Language` HTTP header (first matching supported tag)
  4. Default: `en`

Supported languages: `en`, `uk`.

Usage:
  from i18n_backend import resolve_lang, t

  lang = resolve_lang(request=request, user=user_doc)
  subject = t("otp.email.subject", lang, code=code)

Heavy `Accept-Language` parsing is intentionally avoided — we accept a few
common forms (`uk`, `uk-UA`, `en-US,en;q=0.9,uk;q=0.7`) and pick the first
match against {`en`, `uk`}.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("i18n_backend")

SUPPORTED = ("en", "uk")
DEFAULT_LANG = "en"

# ---------------------------------------------------------------- Dictionary
#
# Keys are flat, dotted. Values may contain {placeholder} tokens — formatted
# at lookup time via str.format(**kwargs). Missing placeholders never raise
# (KeyError is caught and the raw template returned).
#
# Add new keys here as new copy surfaces become locale-aware. EN entries
# double as fallback when UK is missing (or vice-versa).

_DICT: dict[str, dict[str, str]] = {
    "en": {
        # --- OTP email -------------------------------------------------------
        "otp.email.subject": "Your EVA-X code is {code}",
        "otp.email.text": "Your EVA-X sign-in code is {code}. It expires in {minutes} minutes.",
        "otp.email.eyebrow": "EVA-X · sign-in",
        "otp.email.headline": "Continue to your product",
        "otp.email.body": "Use this 6-digit code to sign in. It expires in {minutes} minutes.",
        "otp.email.disclaimer": (
            "If you didn't request this code, ignore this email. Someone may have "
            "entered your address by mistake — your account is safe."
        ),
        "otp.email.footer": "EVA-X · Build products. Not tickets.",
        # --- Notifications (transactional, system-generated) -----------------
        "notif.module_assigned.title": "Module assigned to you",
        "notif.module_assigned.body": "You picked up «{module}». Open it to start.",
        "notif.module_shipped.title": "Module shipped",
        "notif.module_shipped.body": "«{module}» passed QA and is now live.",
        "notif.qa_failed.title": "QA returned a module for fixes",
        "notif.qa_failed.body": "«{module}» needs changes — open the feedback notes.",
        "notif.decision_needed.title": "A decision is waiting for you",
        "notif.decision_needed.body": "Project «{project}» — please review and approve.",
        "notif.payout_sent.title": "Payout sent",
        "notif.payout_sent.body": "{amount} {currency} has been released to your method.",
        "notif.payment_received.title": "Payment received",
        "notif.payment_received.body": "{amount} {currency} from {project} settled.",
        "notif.contract_signed.title": "Contract signed",
        "notif.contract_signed.body": "Contract on «{project}» is now binding for both sides.",
        "notif.deliverable_ready.title": "Deliverable ready for review",
        "notif.deliverable_ready.body": "A new build for «{project}» is waiting.",
        "notif.welcome.title": "Welcome aboard!",
        "notif.welcome.body": "Your account is live. Start with the home tour.",
    },
    "uk": {
        # --- OTP email -------------------------------------------------------
        "otp.email.subject": "Ваш код EVA-X: {code}",
        "otp.email.text": "Ваш код входу в EVA-X: {code}. Він діє {minutes} хв.",
        "otp.email.eyebrow": "EVA-X · вхід",
        "otp.email.headline": "Продовжуйте до вашого продукту",
        "otp.email.body": "Використайте цей 6-значний код для входу. Він діє {minutes} хв.",
        "otp.email.disclaimer": (
            "Якщо ви не запитували цей код — просто проігноруйте лист. "
            "Можливо, хтось випадково вказав вашу адресу — ваш акаунт у безпеці."
        ),
        "otp.email.footer": "EVA-X · Створюйте продукти. Не тікети.",
        # --- Notifications ---------------------------------------------------
        "notif.module_assigned.title": "Вам призначено модуль",
        "notif.module_assigned.body": "Ви взяли в роботу «{module}». Відкрийте, щоб почати.",
        "notif.module_shipped.title": "Модуль здано",
        "notif.module_shipped.body": "«{module}» пройшов QA і вже в продакшні.",
        "notif.qa_failed.title": "QA повернуло модуль на доопрацювання",
        "notif.qa_failed.body": "«{module}» потребує правок — перегляньте коментарі.",
        "notif.decision_needed.title": "Чекає ваше рішення",
        "notif.decision_needed.body": "Проєкт «{project}» — перегляньте та підтвердьте.",
        "notif.payout_sent.title": "Виплату надіслано",
        "notif.payout_sent.body": "{amount} {currency} переказано на ваш спосіб виплат.",
        "notif.payment_received.title": "Платіж отримано",
        "notif.payment_received.body": "{amount} {currency} від {project} зараховано.",
        "notif.contract_signed.title": "Контракт підписано",
        "notif.contract_signed.body": "Контракт по «{project}» тепер обов'язковий для обох сторін.",
        "notif.deliverable_ready.title": "Поставка готова до огляду",
        "notif.deliverable_ready.body": "Нова збірка по «{project}» чекає на вас.",
        "notif.welcome.title": "Ласкаво просимо!",
        "notif.welcome.body": "Ваш акаунт активний. Почніть з туру по головній.",
    },
}


# ---------------------------------------------------------------- Helpers
def _parse_accept_language(header: str) -> list[str]:
    """Return ordered list of language tags from an Accept-Language header.

    Example: `en-US,en;q=0.9,uk;q=0.7` → ['en-us', 'en', 'uk'].
    Quality values are honoured only via their natural order in the header
    (browsers already emit highest-q first); we don't sort by `q` value.
    """
    if not header:
        return []
    out: list[str] = []
    for part in header.split(","):
        tag = part.split(";", 1)[0].strip().lower()
        if tag and tag not in out:
            out.append(tag)
    return out


def _match_supported(tags: list[str]) -> Optional[str]:
    """Pick the first tag that matches a supported language (with base-fallback)."""
    for tag in tags:
        base = tag.split("-", 1)[0]
        if base in SUPPORTED:
            return base
    return None


def resolve_lang(
    request: Any = None,
    user: Optional[dict] = None,
    explicit: Optional[str] = None,
) -> str:
    """Resolve the request's effective language. See module docstring.

    `request` may be a Starlette/FastAPI Request, or anything with a `.headers`
    dict-like attribute. Failures are swallowed — we always return one of
    SUPPORTED.
    """
    # 1. Explicit
    if explicit:
        e = explicit.strip().lower().split("-", 1)[0]
        if e in SUPPORTED:
            return e

    # 2. User preference
    if user:
        lang = (user.get("language") or "").strip().lower().split("-", 1)[0]
        if lang in SUPPORTED:
            return lang

    # 3. Accept-Language header
    if request is not None:
        try:
            header = request.headers.get("accept-language") or request.headers.get(
                "Accept-Language"
            ) or ""
        except Exception:
            header = ""
        match = _match_supported(_parse_accept_language(header))
        if match:
            return match

    return DEFAULT_LANG


def t(key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
    """Translate `key` into `lang`, formatting any {placeholders} with kwargs.

    Falls back to English, then to the key itself if both are missing.
    Format errors return the raw template untouched.
    """
    lang = (lang or DEFAULT_LANG).strip().lower()
    if lang not in SUPPORTED:
        lang = DEFAULT_LANG
    template = _DICT.get(lang, {}).get(key) or _DICT[DEFAULT_LANG].get(key) or key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError) as e:
        logger.debug("i18n format failed for key=%s lang=%s: %s", key, lang, e)
        return template


# Public surface
__all__ = ["resolve_lang", "t", "SUPPORTED", "DEFAULT_LANG"]
