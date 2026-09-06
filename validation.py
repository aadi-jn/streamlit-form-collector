"""Composable validation checks and the ``validate`` orchestrator.

This module is deliberately free of Streamlit and Supabase imports so the rules
stay pure and unit-testable.

A *check* is a callable ``(value) -> str | None`` that returns an error message
when the value is invalid, or ``None`` when it passes. Parameterised checks
(``in_range``, ``matches``, ...) are factories that return such a callable.

Fields declare their checks as an ordered ``rules`` list in ``forms.py``.
``validate(form, values)`` runs them and returns ``{field_name: message}`` for
every field currently failing (first failing rule wins).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Callable, Mapping

Check = Callable[[object], "str | None"]

# A practical email check — not RFC 5322, but rejects the obvious mistakes.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_blank(value: object) -> bool:
    """True for None, empty string, or whitespace-only string."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def required(value: object) -> str | None:
    """Field must have a non-empty value."""
    if _is_blank(value):
        return "This field is required"
    return None


def is_email(value: object) -> str | None:
    """Value looks like an email address. Blank passes (pair with ``required``)."""
    if _is_blank(value):
        return None
    if not _EMAIL_RE.match(str(value).strip()):
        return "Enter a valid email address"
    return None


def is_phone(value: object) -> str | None:
    """Value is a plausible phone number: 7–15 digits, common separators allowed."""
    if _is_blank(value):
        return None
    raw = str(value).strip()
    if not re.match(r"^\+?[0-9\s\-().]+$", raw):
        return "Enter a valid phone number"
    digits = re.sub(r"\D", "", raw)
    if not 7 <= len(digits) <= 15:
        return "Enter a valid phone number"
    return None


def is_number(value: object) -> str | None:
    """Value parses as a number. Blank passes (pair with ``required``)."""
    if _is_blank(value):
        return None
    try:
        float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "Enter a number"
    return None


def is_date(value: object) -> str | None:
    """Value is a real calendar date (``datetime.date`` or ISO ``YYYY-MM-DD``)."""
    if _is_blank(value):
        return None
    if isinstance(value, date):
        return None
    try:
        date.fromisoformat(str(value).strip())
    except ValueError:
        return "Enter a valid date"
    return None


def in_range(minimum: float | None = None, maximum: float | None = None) -> Check:
    """Numeric value falls within [minimum, maximum] (inclusive). Blank passes."""

    def check(value: object) -> str | None:
        if _is_blank(value):
            return None
        try:
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return "Enter a number"
        if minimum is not None and number < minimum:
            return f"Must be at least {_fmt(minimum)}"
        if maximum is not None and number > maximum:
            return f"Must be at most {_fmt(maximum)}"
        return None

    return check


def matches(pattern: "str | re.Pattern[str]", message: str) -> Check:
    """Value matches ``pattern`` (full ``re.match`` semantics). Blank passes."""
    compiled = re.compile(pattern) if isinstance(pattern, str) else pattern

    def check(value: object) -> str | None:
        if _is_blank(value):
            return None
        if not compiled.match(str(value).strip()):
            return message
        return None

    return check


def one_of(options: "list[object]") -> Check:
    """Value is one of ``options``. Blank passes (pair with ``required``)."""
    allowed = list(options)

    def check(value: object) -> str | None:
        if _is_blank(value):
            return None
        if value not in allowed:
            return "Choose one of the allowed options"
        return None

    return check


def _fmt(number: float) -> str:
    """Render a bound without a trailing ``.0`` for whole numbers."""
    return str(int(number)) if float(number).is_integer() else str(number)


def validate(form: Mapping, values: Mapping) -> dict[str, str]:
    """Run every field's rules against ``values``.

    Returns ``{field_name: message}`` for each failing field (first failing rule
    wins). An empty dict means the form is clean and safe to submit.
    """
    errors: dict[str, str] = {}
    for field in form["fields"]:
        name = field["name"]
        value = values.get(name)
        for rule in field.get("rules", []):
            message = rule(value)
            if message:
                errors[name] = message
                break
    return errors
