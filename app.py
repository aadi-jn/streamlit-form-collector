"""Public form page.

Streamlit re-runs this script top-to-bottom on every widget interaction. We
lean on that instead of callbacks:

1. Render each field with a stable ``key``; current values live in session_state.
2. After rendering, call ``validate(form, values)`` for the whole form.
3. Show each field's error immediately below it — but only once the field has
   been touched, so the form isn't red on first load. A field "commits" its
   value (and fires ``on_change``) on Enter or blur, not per keystroke — that's
   a Streamlit limitation for text/number inputs.
4. Because of (3), the Submit button is **always enabled**: disabling it would
   trap the user whenever the last field they typed in still holds focus (its
   value not yet sent to the server), and a disabled button also swallows the
   click that would have committed that field.
5. On submit we re-run ``validate()`` server-side. Clicking Submit blurs and
   commits the focused field, so this sees the final values; if anything fails
   we mark every field touched and show all errors inline. This server-side
   check — not the button — is what blocks a bad submission.
"""

from __future__ import annotations

import streamlit as st

from db import insert_submission
from forms import DEFAULT_FORM_ID, FORMS
from validation import validate

st.set_page_config(page_title="Form", page_icon="📝")

form = FORMS[DEFAULT_FORM_ID]


def _key(name: str) -> str:
    return f"{form['id']}__{name}"


def _mark_touched(name: str) -> None:
    st.session_state.setdefault("_touched", set()).add(name)


def _render_field(field: dict) -> None:
    name = field["name"]
    key = _key(name)
    label = field["label"]
    widget = field["widget"]
    help_text = field.get("help")
    on_change = lambda n=name: _mark_touched(n)  # noqa: E731

    if widget == "text":
        st.text_input(label, key=key, help=help_text, on_change=on_change)
    elif widget == "number":
        st.number_input(
            label, key=key, help=help_text, value=None, step=1, on_change=on_change
        )
    elif widget == "select":
        st.selectbox(
            label,
            field["options"],
            key=key,
            help=help_text,
            index=None,
            placeholder="Choose an option",
            on_change=on_change,
        )
    elif widget == "date":
        st.date_input(
            label, key=key, help=help_text, value=None, on_change=on_change
        )
    else:  # pragma: no cover - programmer error
        raise ValueError(f"unknown widget: {widget!r}")


def _collect_values() -> dict:
    return {f["name"]: st.session_state.get(_key(f["name"])) for f in form["fields"]}


def _user_agent() -> str | None:
    try:
        return st.context.headers.get("User-Agent")
    except Exception:
        return None


def _clear_form() -> None:
    for field in form["fields"]:
        st.session_state.pop(_key(field["name"]), None)
    st.session_state.pop("_touched", None)


st.title(form["title"])

if st.session_state.pop("_submitted_ok", False):
    st.success("Thanks — your response has been recorded.")

touched: set[str] = st.session_state.setdefault("_touched", set())

for field in form["fields"]:
    _render_field(field)
    name = field["name"]
    errors_so_far = validate(form, _collect_values())
    if name in touched and name in errors_so_far:
        st.caption(f":red[{errors_so_far[name]}]")

errors = validate(form, _collect_values())
if errors and touched:
    st.warning("Some answers still need fixing — see the notes in red above.")

if st.button("Submit", type="primary"):
    # The button is never disabled; this server-side check is the real gate.
    values = _collect_values()
    errors = validate(form, values)
    if errors:
        # Reveal every outstanding error inline (this run) and keep them shown
        # on the next run too.
        st.session_state["_touched"] = {f["name"] for f in form["fields"]}
        labels = {f["name"]: f["label"] for f in form["fields"]}
        st.error(
            "Couldn't submit — please fix:\n"
            + "\n".join(f"- **{labels[n]}**: {m}" for n, m in errors.items())
        )
    else:
        insert_submission(form["id"], values, _user_agent())
        st.session_state["_submitted_ok"] = True
        _clear_form()
        st.rerun()
