# Form Collector

A self-hosted form app: a public (no-login) Streamlit form that validates input as you move
through it, shows inline errors, blocks a bad submission server-side, and stores each valid
submission in a Supabase Postgres database. A separate password-gated page lets the owner
review submissions and export CSV.

See [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) for full scope and the definition of done, and
[`CLAUDE.md`](CLAUDE.md) for the architecture.

## Layout

| File | Responsibility |
|---|---|
| `app.py` | Public form page. Renders fields, runs live validation, gates submit. |
| `pages/1_Admin.py` | Password-gated submissions table + CSV download. |
| `forms.py` | Declarative field definitions. Forms are hard-coded here in v1. |
| `validation.py` | Composable check functions + `validate()`. No Streamlit/Supabase imports. |
| `db.py` | The only module that talks to Supabase. |
| `schema.sql` | `submissions` table DDL + RLS policy + `grant insert` to `anon`. Run in the Supabase SQL editor. |
| `tests/` | `test_validation.py` (pure) + `test_app_smoke.py` (Streamlit `AppTest`). |
| `scripts/smoke_supabase.py` | Checks the DB security contract against a live project. |

## Setup

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Create the Supabase project

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor → New query**, paste the contents of [`schema.sql`](schema.sql), and
   run it. This creates `public.submissions`, enables RLS, and adds an insert-only policy
   for the `anon` role.
3. Open **Project Settings → API** and copy:
   - the **Project URL**,
   - the **`anon` `public`** key,
   - the **`service_role`** key (under "Project API keys" — reveal it).

### 3. Configure secrets

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with the URL and keys from step 2, and choose an
`ADMIN_PASSWORD`. This file is gitignored — never commit it.

### 4. Run locally

```bash
streamlit run app.py
```

The public form is at `/`; the admin page is in the sidebar as **Admin** (or
`http://localhost:8501/Admin`), gated by `ADMIN_PASSWORD`.

## Tests

```bash
pytest                                            # all (50; offline, no DB needed)
pytest tests/test_validation.py::test_one_of      # single test
python scripts/smoke_supabase.py                  # DB security contract (needs secrets.toml)
```

## Deploy (Streamlit Community Cloud)

1. Push this repo to **public** GitHub (it must be public so Community Cloud can build it
   without extra access grants — which is why nothing sensitive is committed).
2. On [share.streamlit.io](https://share.streamlit.io), create an app pointed at `app.py`.
3. In **App → Settings → Secrets**, paste the same four keys from your local
   `secrets.toml`.
4. Deploy. The admin page is reachable at `<your-app-url>/Admin`.

## Adding a form

Add a new entry to `FORMS` in `forms.py` and point `DEFAULT_FORM_ID` at it. A field is
required (and shows a red `*`) when `required` is in its `rules`. New validation rules are
small functions in `validation.py`. Nothing else needs to change.

## Definition of done checklist

From `PROJECT_BRIEF.md` — verify after deploy:

- [ ] Invalid input shows the right inline error and blocks submit.
- [ ] Valid input creates exactly one row in `submissions` with the expected JSON.
- [ ] The admin page lists all submissions; CSV export row count matches the table.
- [ ] Insert 5 known test submissions → `select count(*) from submissions` = 5, JSON matches.
- [ ] The `anon` key cannot read submissions (RLS blocks `SELECT`).
- [ ] App runs on a clean machine from this README alone.
