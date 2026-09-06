"""Password-gated page to review submissions and export CSV.

Reads with the service_role key (via ``db.fetch_submissions``), which bypasses
RLS. The key stays server-side in ``st.secrets``; only the rendered table and
the CSV reach the browser.

The password gate is a simple ``st.secrets["ADMIN_PASSWORD"]`` comparison. This
page's URL is publicly reachable on a multipage deployment — the password is
what protects it.
"""

from __future__ import annotations

import hmac

import pandas as pd
import streamlit as st

from db import fetch_submissions

st.set_page_config(page_title="Admin — submissions", page_icon="🔒")
st.title("Submissions")


def _check_password() -> bool:
    if st.session_state.get("admin_ok"):
        return True

    with st.form("login"):
        entered = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Unlock")

    if submitted:
        if hmac.compare_digest(entered, st.secrets["ADMIN_PASSWORD"]):
            st.session_state["admin_ok"] = True
            return True
        st.error("Incorrect password.")
    return False


if not _check_password():
    st.stop()

rows = fetch_submissions()

if not rows:
    st.info("No submissions yet.")
    st.stop()

# Flatten: top-level columns + one column per answer key in ``data``.
frame = pd.DataFrame(rows)
answers = pd.json_normalize(frame["data"]).add_prefix("data.")
table = pd.concat([frame.drop(columns=["data"]), answers], axis=1)

st.caption(f"{len(table)} submission(s)")
st.dataframe(table, width="stretch", hide_index=True)

st.download_button(
    "Download CSV",
    table.to_csv(index=False).encode("utf-8"),
    file_name="submissions.csv",
    mime="text/csv",
)
