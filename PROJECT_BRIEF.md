# Project Brief: Form Collector (Streamlit + Supabase)

**Author:** Aadi Jain   **Date:** 2026-09-06   **Est. effort:** ~3–5 days for a working v1

**Status (2026-09-06):** v1 works end-to-end against a live Supabase project — all modules,
a placeholder form (`contact_v1`), 44 passing validation tests, and the DoD security /
insert / admin / CSV checks all verified. Remaining: define the real first form, deploy to
Streamlit Community Cloud, and re-run the DoD on the deployed app. See `CLAUDE.md` for the
as-built architecture.

---

## 1. The question / goal

Can I stand up a self-hosted form app that lets people fill out a form, validates their
answers **live as they type**, shows inline errors, and reliably stores every valid
submission in Supabase — with a simple page for me to review what's been collected?

This is a build project, not an analysis. Success = a deployed app I can send a link to.

## 2. Why it matters (the "so what")

Off-the-shelf form tools (Google Forms, Typeform, Tally) don't give me full control over
validation logic or where the data lands. Owning the app means:

- Validation rules are exactly what I want, enforced before bad data is ever stored.
- All responses sit in my own Supabase Postgres database, queryable with SQL and joinable
  with other data later.
- It's a reusable foundation — new forms are just new field definitions in code.

## 3. Scope (decisions made)

| Area | Decision |
|---|---|
| Respondents | **Public link, no login.** Anyone with the URL can submit. |
| Form definition | **Hard-coded in the app** (Python). One form to start; structured so more can be added. |
| Validation (v1) | **Format checks:** required fields, email format, phone format, number ranges, date validity, regex/pattern, allowed-value lists. |
| Admin side | **A "View submissions" page** — a table of all responses, password-protected. |
| Data store | Supabase Postgres, one `submissions` table. Insert via `supabase-py`. |
| Deployment | Streamlit Community Cloud (free), secrets stored in Streamlit's secrets manager. |

## 4. Data

- **Store:** Supabase project → Postgres → `public.submissions` table.
- **Grain:** one row per completed form submission.
- **Proposed schema:**

  | column | type | notes |
  |---|---|---|
  | `id` | `uuid` default `gen_random_uuid()` | primary key |
  | `submitted_at` | `timestamptz` default `now()` | server-set |
  | `form_id` | `text` | which form (e.g. `"signup_v1"`) — future-proofing |
  | `data` | `jsonb` | all answers as a JSON object |
  | `user_agent` | `text` nullable | light context, optional |

  Storing answers in a single `jsonb` column keeps the schema stable as form fields
  change. If one specific form stabilizes and needs heavy querying, promote its fields
  to real columns later.

- **Access control (Supabase Row Level Security):**
  - Enable RLS on `submissions`.
  - Policy 1: allow `INSERT` for the `anon` role (public submissions), no `SELECT`.
  - Admin reads use the **service_role key** (kept in Streamlit secrets, never shipped
    to the browser) — or a dedicated Postgres view/role. Never expose `service_role`
    in client-side code.
- **Freshness:** real-time. Each submission is an immediate insert.

## 5. How live validation works (the core mechanic)

Streamlit re-runs the whole script top-to-bottom on every widget interaction. We use that:

1. Render each field with a `key`; read current values from `st.session_state`.
2. After rendering, run a `validate(values)` function that returns
   `{field_name: error_message}` for every field currently failing.
3. Render each field's error immediately below it (e.g. `st.caption` in red, or
   `st.error`) whenever that field has been touched.
4. The **Submit button is disabled** until `validate()` returns no errors.
5. On submit: re-validate server-side, then `INSERT` into Supabase. Show a success
   message and clear the form.

Validation rules live in one module (`validation.py`) as small composable functions
(`required`, `is_email`, `in_range`, `matches`, …) so they're easy to test and reuse.

## 6. Deliverable

A deployed Streamlit app with:

- `app.py` — form page with live inline validation + submit.
- `pages/1_Admin.py` — password-gated submissions table with CSV download (Streamlit multipage).
- `forms.py` — the form's field definitions (label, type, rules, options).
- `validation.py` — reusable validation functions + the `validate()` orchestrator.
- `db.py` — Supabase client + `insert_submission()` / `fetch_submissions()`.
- `schema.sql` — table + RLS policies, runnable in the Supabase SQL editor.
- `README.md` — setup, secrets, deploy steps.

## 7. Definition of done

- [ ] Submitting a form with invalid input shows the right inline error and blocks submit.
- [ ] Submitting valid input creates exactly one row in `submissions` with the expected JSON.
- [ ] The admin page lists all submissions and CSV export matches the table row count.
- [ ] **Validation check:** insert 5 known test submissions; `SELECT count(*)` in Supabase = 5,
      and the JSON of each matches what was typed.
- [ ] The `anon` key cannot read submissions (verify RLS blocks `SELECT`).
- [ ] App runs on a clean machine from the README alone.

## 8. Out of scope (v1)

- User accounts / login for respondents.
- Cross-field validation, uniqueness ("already submitted") checks, length/word-count limits.
  (Planned next — see follow-ups.)
- In-app form builder / editing forms without code changes.
- File uploads, multi-page forms, save-and-resume.
- Email notifications, webhooks, analytics dashboards.
- Editing or deleting submissions from the app.

## 9. Open questions / follow-ups

- **v2 validation:** cross-field rules (date ordering, conditional-required), uniqueness
  check against Supabase, min/max length.
- **What's the actual first form?** (fields, options, exact rules) — still open. The skeleton
  ships a placeholder `contact_v1`; the real form replaces it as a new `FORMS` entry.
- Expected volume? (affects whether Community Cloud is enough or we need a paid host.)
- Do submissions ever need to be edited/corrected? (would add an admin edit view.)
- Retention / privacy: how long is data kept, any PII handling requirements?

---

## Suggested build order

1. ✅ ~~Create Supabase project; run `schema.sql`; confirm RLS.~~ *(ref `ocprrutmukogmtykgbfg`; `scripts/smoke_supabase.py` passes)*
2. ✅ ~~`db.py` — connect, insert a row.~~
3. ✅ ~~`forms.py` + `validation.py` — first form + rules; unit-test `validate()`.~~ *(placeholder `contact_v1`; 44 tests)*
4. ✅ ~~`app.py` — render fields, wire live validation, disable submit until clean.~~
5. ✅ ~~Wire submit → `insert_submission()`; test end-to-end.~~ *(5 submissions via AppTest → 5 rows, JSON verified)*
6. ✅ ~~`admin.py` — password gate + table + CSV download.~~ *(`pages/1_Admin.py`; CSV row count matches)*
7. **Deploy to Streamlit Community Cloud; move keys into secrets; re-run the DoD on the live app.** — next
