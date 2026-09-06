"""Declarative form definitions.

Forms are hard-coded here in v1 — no form-builder UI, no DB-stored config.
Adding a form or a rule should mean editing *only* this file.

Each field is a dict:

    {
        "name":    str,              # key in session_state and in the stored JSON
        "label":   str,              # shown to the user
        "widget":  "text" | "number" | "select" | "date",
        "options": list[str],        # required for "select"
        "help":    str,              # optional caption under the field
        "rules":   list[Check],      # ordered; first failure wins
    }

A form is a dict: ``{"id": str, "title": str, "fields": [...]}``.
``FORMS`` maps ``form_id -> form``. ``app.py`` renders ``DEFAULT_FORM_ID``.
"""

from __future__ import annotations

import re

from validation import (
    in_range,
    is_email,
    is_phone,
    matches,
    one_of,
    required,
)

# Module-level patterns, passed to ``matches``.
URL_RE = re.compile(r"^https?://[^\s.]+\.[^\s]+$", re.IGNORECASE)
LINKEDIN_RE = re.compile(
    r"^https?://(www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?$", re.IGNORECASE
)

_TOPICS = ["Sales", "Support", "Feedback", "Other"]

# Placeholder form. Exercises every validation type end-to-end; swap in the real
# form by adding a new entry here and pointing DEFAULT_FORM_ID at it.
CONTACT_V1 = {
    "id": "contact_v1",
    "title": "Contact us",
    "fields": [
        {
            "name": "full_name",
            "label": "Full name",
            "widget": "text",
            "rules": [required],
        },
        {
            "name": "email",
            "label": "Email",
            "widget": "text",
            "rules": [required, is_email],
        },
        {
            "name": "phone",
            "label": "Phone",
            "widget": "text",
            "help": "Include country code, e.g. +1 555 123 4567",
            "rules": [required, is_phone],
        },
        {
            "name": "age",
            "label": "Age",
            "widget": "number",
            "rules": [required, in_range(18, 120)],
        },
        {
            "name": "topic",
            "label": "Topic",
            "widget": "select",
            "options": _TOPICS,
            "rules": [required, one_of(_TOPICS)],
        },
        {
            "name": "linkedin",
            "label": "LinkedIn profile",
            "widget": "text",
            "help": "e.g. https://www.linkedin.com/in/your-name",
            "rules": [required, matches(LINKEDIN_RE, "Enter a linkedin.com/in/ profile URL")],
        },
        {
            "name": "website",
            "label": "Website (optional)",
            "widget": "text",
            "rules": [matches(URL_RE, "Enter a valid URL (including https://)")],
        },
    ],
}

FORMS = {CONTACT_V1["id"]: CONTACT_V1}

DEFAULT_FORM_ID = "contact_v1"
