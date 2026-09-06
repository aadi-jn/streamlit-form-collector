"""The only module that talks to Supabase.

Two clients, two jobs:

* the **anon** client is used by the public form and may only INSERT
  (RLS enforces this server-side);
* the **service_role** client is used by the admin page to read submissions
  back — it bypasses RLS, so its key must never reach the browser.

Both keys, the project URL, and the admin password come from ``st.secrets``
(local: ``.streamlit/secrets.toml``; production: the Community Cloud secrets
manager). See ``.streamlit/secrets.toml.example``.
"""

from __future__ import annotations

from typing import Any

import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def _client(role: str) -> Client:
    """Build (and cache) a Supabase client for ``role`` in {"anon", "service_role"}."""
    url = st.secrets["SUPABASE_URL"]
    if role == "anon":
        key = st.secrets["SUPABASE_ANON_KEY"]
    elif role == "service_role":
        key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    else:  # pragma: no cover - programmer error
        raise ValueError(f"unknown role: {role!r}")
    return create_client(url, key)


def insert_submission(
    form_id: str, data: dict[str, Any], user_agent: str | None = None
) -> dict[str, Any]:
    """Insert one submission using the anon client. Returns the stored row."""
    payload = {"form_id": form_id, "data": data, "user_agent": user_agent}
    response = _client("anon").table("submissions").insert(payload).execute()
    return response.data[0] if response.data else payload


def fetch_submissions() -> list[dict[str, Any]]:
    """Return all submissions, newest first, using the service_role client."""
    response = (
        _client("service_role")
        .table("submissions")
        .select("*")
        .order("submitted_at", desc=True)
        .execute()
    )
    return response.data or []
