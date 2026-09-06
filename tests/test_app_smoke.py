"""Headless checks of the form page via Streamlit's AppTest.

These don't touch Supabase — they cover rendering, the live-error display, and
the invalid-submit path (which never calls the DB). The valid-submit path is
exercised by ``scripts/smoke_supabase.py`` and manual/e2e testing against a
live project.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _fresh():
    return AppTest.from_file(APP, default_timeout=30).run()


def test_renders_all_fields_no_error_on_first_load():
    at = _fresh()
    assert [t.value for t in at.title] == ["Contact us"]
    starts = {w.label.split(" :red")[0].strip() for w in at.text_input}
    assert starts == {"Full name", "Email", "Phone", "LinkedIn profile", "Website"}
    # only the required-legend caption, no field error captions
    assert [c.value for c in at.caption] == ["Fields marked :red[\\*] are required."]
    assert not at.exception


def test_required_fields_get_an_asterisk_optional_ones_do_not():
    at = _fresh()
    marked = {w.label.split(" :red")[0].strip() for w in at.text_input if ":red[\\*]" in w.label}
    assert marked == {"Full name", "Email", "Phone"}  # not LinkedIn, not Website
    assert "\\*" in at.number_input[0].label  # Age
    assert "\\*" in at.selectbox[0].label  # Topic


def test_submit_button_is_enabled_even_when_form_is_empty():
    # Deliberate: a disabled button traps users whose last field still has focus.
    at = _fresh()
    assert at.button[0].label == "Submit"
    assert not at.button[0].disabled


def test_touched_field_shows_inline_error():
    at = _fresh()
    at.text_input(key="contact_v1__email").set_value("nope").run()
    assert any("valid email" in c.value for c in at.caption)


def test_invalid_submit_lists_every_error_and_does_not_raise():
    at = _fresh()
    at.text_input(key="contact_v1__full_name").set_value("Aadi Jain").run()
    at.button[0].click().run()
    assert not at.exception
    blob = " ".join(e.value for e in at.error)
    assert "Couldn't submit" in blob
    assert "Email" in blob and "Phone" in blob and "Age" in blob
    assert "LinkedIn" not in blob  # optional, left blank


def test_fully_valid_form_shows_no_errors():
    at = _fresh()
    at.text_input(key="contact_v1__full_name").set_value("Aadi Jain").run()
    at.text_input(key="contact_v1__email").set_value("a@b.co").run()
    at.text_input(key="contact_v1__phone").set_value("9650424680").run()
    at.number_input(key="contact_v1__age").set_value(36).run()
    at.selectbox(key="contact_v1__topic").set_value("Sales").run()
    # linkedin + website left blank (both optional)
    # No field error captions — only the required-fields legend remains.
    assert [c.value for c in at.caption] == ["Fields marked :red[\\*] are required."]
