# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Pre-code. The only content so far is `PROJECT_BRIEF.md`, which defines the app being built.
This file describes the **intended** architecture from that brief so future sessions don't
re-derive it. Update the Commands section below once scaffolding exists, and revise the
architecture here whenever it diverges from what actually gets built.

## What this app is

A self-hosted form-collection app: a public (no-login) Streamlit form that validates input
**live as the user types**, shows inline errors, blocks submission until clean, and stores
each valid submission in a Supabase Postgres database. A separate password-gated page lets
the owner review submissions and export CSV. See `PROJECT_BRIEF.md` for full scope,
definition of done, and what is explicitly out of scope for v1.

Stack: Streamlit (UI + server), Supabase (`supabase-py` client) over Postgres, deployed on
Streamlit Community Cloud from a **public** GitHub repo.

## Commands

_To be filled in once the project is scaffolded._ Expected shape:

- Install: `pip install -r requirements.txt`
- Run locally: `streamlit run app.py`
- Tests: `pytest` (single test: `pytest tests/test_validation.py::test_name`)

## Intended architecture

Planned module layout (single-package, flat):

| File | Responsibility |
|---|---|
| `app.py` | Public form page. Renders fields, runs live validation, gates submit. |
| `admin.py` | Password-gated submissions table + CSV download. (Or a `pages/` entry.) |
| `forms.py` | Declarative field definitions for each form: label, widget type, options, validation rules. Forms are **hard-coded here** in v1 — no form-builder UI, no DB-stored form config. |
| `validation.py` | Small composable check functions (`required`, `is_email`, `in_range`, `matches`, ...) plus `validate(form, values) -> {field: error_message}`. Pure functions, no Streamlit or DB imports — keep it unit-testable. |
| `db.py` | Supabase client construction + `insert_submission()` / `fetch_submissions()`. The only module that talks to Supabase. |
| `schema.sql` | `submissions` table DDL + RLS policies. Run in the Supabase SQL editor. |

### The live-validation mechanic (core design point)

Streamlit re-runs the whole script top-to-bottom on every widget interaction. The app
relies on this instead of callbacks:

1. Render each field with a stable `key`; current values come from `st.session_state`.
2. After rendering all fields, call `validate(form, values)` — returns a dict of
   `{field_name: error_message}` for every field currently failing.
3. Render each field's error immediately below it, but only once that field has been
   touched (track touched-state in `session_state` so the form isn't red on first load).
4. The **Submit button is `disabled=` while the error dict is non-empty.**
5. On submit, **re-run `validate()` server-side** before inserting — never trust the
   disabled button alone.

Keep validation rules declarative in `forms.py` and the logic in `validation.py`. Adding a
rule should not require touching `app.py`.

### Data model

One row per submission in `public.submissions`:

- `id uuid` (default `gen_random_uuid()`), `submitted_at timestamptz` (default `now()`),
  `form_id text`, `data jsonb` (all answers as one object), `user_agent text` nullable.
- Answers live in a single `jsonb` column so the table schema is stable as form fields
  change. Promote fields to real columns only if a specific form stabilizes and needs
  heavy querying.

### Supabase security — do not get this wrong

- RLS is **enabled** on `submissions`.
- The public app uses the **anon key** and may only `INSERT`. No `SELECT` policy for `anon`.
- The admin page reads with the **`service_role` key**, which must stay server-side only
  (Streamlit secrets / `st.secrets`) and must never be sent to the browser or committed.
- Secrets: local dev uses `.streamlit/secrets.toml` (gitignored); production uses the
  Streamlit Community Cloud secrets manager. Keys: Supabase URL, anon key, service_role
  key, and the admin page password.

## Deployment

Public GitHub repo → Streamlit Community Cloud app pointed at `app.py`. Because the repo is
public, **nothing sensitive may be committed** — all credentials go through the secrets
manager. The repo is intentionally public so Community Cloud can build it without extra
access grants.

## Conventions

- `validation.py` stays free of Streamlit and Supabase imports.
- `db.py` is the single choke point for Supabase access.
- New forms = new entries in `forms.py`, nothing else.
