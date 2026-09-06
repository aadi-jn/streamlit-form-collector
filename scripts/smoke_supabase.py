"""End-to-end smoke test against a live Supabase project.

Run this AFTER creating the project and running schema.sql, with
`.streamlit/secrets.toml` filled in:

    python scripts/smoke_supabase.py

It checks the three things the definition of done cares about:

1. the anon key CAN insert a submission,
2. the anon key CANNOT read submissions back (RLS),
3. the service_role key CAN read them back.

It inserts one clearly-marked test row (form_id = "smoke_test") and leaves it —
delete it from the table afterwards if you like.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from supabase import create_client

SECRETS = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"


def main() -> int:
    if not SECRETS.exists():
        print(f"missing {SECRETS} — copy from .streamlit/secrets.toml.example")
        return 1

    cfg = tomllib.loads(SECRETS.read_text())
    url = cfg["SUPABASE_URL"]
    anon = create_client(url, cfg["SUPABASE_ANON_KEY"])
    service = create_client(url, cfg["SUPABASE_SERVICE_ROLE_KEY"])

    ok = True

    # 1. anon insert
    try:
        anon.table("submissions").insert(
            {"form_id": "smoke_test", "data": {"hello": "world"}, "user_agent": "smoke"}
        ).execute()
        print("PASS  anon can insert")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL  anon insert raised: {exc}")
        ok = False

    # 2. anon cannot read
    try:
        res = anon.table("submissions").select("*").execute()
        if res.data:
            print(f"FAIL  anon SELECT returned {len(res.data)} row(s) — RLS not blocking reads")
            ok = False
        else:
            print("PASS  anon SELECT returns nothing (RLS blocking reads)")
    except Exception as exc:  # noqa: BLE001
        print(f"PASS  anon SELECT raised (RLS blocking reads): {exc}")

    # 3. service_role can read
    try:
        res = service.table("submissions").select("*").order("submitted_at", desc=True).execute()
        print(f"PASS  service_role can read — {len(res.data)} row(s) in table")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL  service_role read raised: {exc}")
        ok = False

    print("\nAll checks passed." if ok else "\nSome checks FAILED — see above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
