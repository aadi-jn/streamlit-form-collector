"""Unit tests for the validation checks and the ``validate`` orchestrator."""

from __future__ import annotations

import re
from datetime import date

import pytest

from forms import FORMS
from validation import (
    in_range,
    is_date,
    is_email,
    is_number,
    is_phone,
    matches,
    one_of,
    required,
    validate,
)


# --- individual checks ---------------------------------------------------------

@pytest.mark.parametrize("value", ["", "   ", None])
def test_required_rejects_blank(value):
    assert required(value) == "This field is required"


@pytest.mark.parametrize("value", ["x", "0", 0, False])
def test_required_accepts_present(value):
    assert required(value) is None


@pytest.mark.parametrize("value", ["a@b.co", "first.last@example.org"])
def test_is_email_accepts(value):
    assert is_email(value) is None


@pytest.mark.parametrize("value", ["no-at", "a@b", "a b@c.com", "@example.com"])
def test_is_email_rejects(value):
    assert is_email(value) == "Enter a valid email address"


def test_is_email_blank_passes():
    assert is_email("") is None


@pytest.mark.parametrize("value", ["+1 555 123 4567", "5551234567", "(555) 123-4567"])
def test_is_phone_accepts(value):
    assert is_phone(value) is None


@pytest.mark.parametrize("value", ["123", "phone", "+1-800-CALL", "1234567890123456"])
def test_is_phone_rejects(value):
    assert is_phone(value) == "Enter a valid phone number"


@pytest.mark.parametrize("value", ["3.14", "42", -1, 2.0])
def test_is_number_accepts(value):
    assert is_number(value) is None


@pytest.mark.parametrize("value", ["abc", "1,000", "12x"])
def test_is_number_rejects(value):
    assert is_number(value) == "Enter a number"


def test_in_range_inclusive_bounds():
    check = in_range(18, 120)
    assert check(18) is None
    assert check(120) is None
    assert check(17) == "Must be at least 18"
    assert check(121) == "Must be at most 120"


def test_in_range_blank_passes():
    assert in_range(0, 10)("") is None


def test_in_range_non_numeric():
    assert in_range(0, 10)("abc") == "Enter a number"


def test_matches_pattern():
    check = matches(re.compile(r"^A\d+$"), "bad code")
    assert check("A123") is None
    assert check("B123") == "bad code"
    assert check("") is None


def test_matches_accepts_string_pattern():
    check = matches(r"^\d{3}$", "need 3 digits")
    assert check("123") is None
    assert check("12") == "need 3 digits"


def test_one_of():
    check = one_of(["Sales", "Support"])
    assert check("Sales") is None
    assert check("Other") == "Choose one of the allowed options"
    assert check("") is None


@pytest.mark.parametrize("value", ["2026-09-06", date(2026, 9, 6)])
def test_is_date_accepts(value):
    assert is_date(value) is None


@pytest.mark.parametrize("value", ["2026-13-01", "not-a-date", "09/06/2026"])
def test_is_date_rejects(value):
    assert is_date(value) == "Enter a valid date"


# --- validate() orchestrator -------------------------------------------------

CONTACT = FORMS["contact_v1"]

VALID_VALUES = {
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "+1 555 123 4567",
    "age": 32,
    "topic": "Support",
    "linkedin": "https://www.linkedin.com/in/ada-lovelace",
    "website": "",  # optional, blank is fine
}


def test_validate_clean_form_returns_empty():
    assert validate(CONTACT, VALID_VALUES) == {}


def test_validate_reports_first_failing_rule_per_field():
    values = dict(VALID_VALUES, email="", age=5)
    errors = validate(CONTACT, values)
    assert errors["email"] == "This field is required"  # required beats is_email
    assert errors["age"] == "Must be at least 18"
    assert set(errors) == {"email", "age"}


def test_validate_optional_website_rejects_bad_value_but_allows_blank():
    assert "website" not in validate(CONTACT, VALID_VALUES)
    bad = dict(VALID_VALUES, website="not a url")
    assert validate(CONTACT, bad)["website"] == "Enter a valid URL (including https://)"


def test_validate_linkedin_pattern():
    bad = dict(VALID_VALUES, linkedin="https://twitter.com/ada")
    assert validate(CONTACT, bad)["linkedin"] == "Enter a linkedin.com/in/ profile URL"


def test_validate_missing_value_treated_as_blank():
    # ``age`` and others absent entirely from the mapping.
    errors = validate(CONTACT, {})
    assert errors["full_name"] == "This field is required"
    assert errors["age"] == "This field is required"
