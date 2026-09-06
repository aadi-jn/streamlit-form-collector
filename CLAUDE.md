# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

v1 works end-to-end against a live Supabase project (ref `ocprrutmukogmtykgbfg`), verified:
anon insert OK, anon SELECT blocked by RLS, admin page reads + CSV. `forms.py` still holds
the **placeholder** `contact_v1` form — swap in the real form when defined (add a `FORMS`
entry, point `DEFAULT_FORM_ID` at it). **Not yet deployed** to Streamlit Community Cloud.
`pytest` (44 validation tests) passes offline; `app.py` / `pages/1_Admin.py` need
`.streamlit/secrets.toml`. `scripts/smoke_supabase.py` re-checks the DB security contract.

## What this app is

A self-hosted form-collection app: a public (no-login) Streamlit form that validates input
**live as the user types**, shows inline errors, blocks submission until clean, and stores
each valid submission in a Supabase Postgres database. A separate password-gated page lets
the owner review submissions and export CSV. See `PROJECT_BRIEF.md` for full scope,
definition of done, and what is explicitly out of scope for v1.

Stack: Streamlit (UI + server), Supabase (`supabase-py` client) over Postgres, deployed on
Streamlit Community Cloud from a **public** GitHub repo.

## Commands

- Install: `pip install -r requirements.txt`
- Run locally: `streamlit run app.py` (needs `.streamlit/secrets.toml` — copy from
  `.streamlit/secrets.toml.example`)
- Tests: `pytest` (single test: `pytest tests/test_validation.py::test_validate_clean_form_returns_empty`)
- Admin page: sidebar **Admin** entry, or `/Admin` — gated by `ADMIN_PASSWORD`

## Architecture

Module layout (single-package, flat):

| File | Responsibility |
|---|---|
| `app.py` | Public form page. Renders fields, runs live validation, gates submit. |
| `pages/1_Admin.py` | Password-gated submissions table + CSV download (Streamlit multipage). Uses `pandas` to flatten `data` JSON into columns. |
| `forms.py` | Declarative field definitions: `FORMS` maps `form_id -> {id, title, fields}`; each field is `{name, label, widget, options?, help?, rules}`. `DEFAULT_FORM_ID` is what `app.py` renders. Forms are **hard-coded here** in v1 — no form-builder UI, no DB-stored form config. |
| `validation.py` | Composable checks — `required`, `is_email`, `is_phone`, `is_number`, `is_date`, and the factories `in_range(min, max)`, `matches(pattern, message)`, `one_of(options)` — plus `validate(form, values) -> {field: error_message}` (first failing rule per field wins). Each check is `(value) -> str | None`; blank passes every check except `required`. Pure functions, no Streamlit or DB imports. |
| `db.py` | Supabase client construction + `insert_submission()` / `fetch_submissions()`. The only module that talks to Supabase. |
| `schema.sql` | `submissions` table DDL + RLS policy. Re-runnable. Run in the Supabase SQL editor. |
| `tests/test_validation.py` | Unit tests for every check and `validate()`. |

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
- **Two gotchas we hit (both fixed):** (1) `schema.sql` must `grant insert ... to anon` —
  the RLS policy alone isn't enough, and Supabase's default privileges don't reliably
  cover tables created in the SQL editor. (2) `insert_submission` must use
  `returning=ReturnMethod.minimal`; with no anon SELECT policy, the default representation
  read-back after INSERT fails with a misleading `42501 "new row violates row-level
  security policy"`.

## Deployment

Public GitHub repo → Streamlit Community Cloud app pointed at `app.py`. Because the repo is
public, **nothing sensitive may be committed** — all credentials go through the secrets
manager. The repo is intentionally public so Community Cloud can build it without extra
access grants.

## Conventions

- `validation.py` stays free of Streamlit and Supabase imports.
- `db.py` is the single choke point for Supabase access.
- New forms = new entries in `forms.py`, nothing else.
