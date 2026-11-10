"""Apply db/migrations/*.sql in order, once each (recorded in public.schema_migrations).

python -m jobs.migrate            # apply pending
python -m jobs.migrate --status   # list applied / pending
"""

from __future__ import annotations

import argparse
from pathlib import Path

from finn.db import connect

MIGRATIONS = Path(__file__).resolve().parents[1] / "db" / "migrations"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    files = sorted(MIGRATIONS.glob("*.sql"))
    with connect() as conn:
        conn.execute(
            "create table if not exists public.schema_migrations "
            "(name text primary key, applied_at timestamptz not null default now())"
        )
        conn.execute("alter table public.schema_migrations enable row level security")
        applied = {r["name"] for r in conn.execute("select name from public.schema_migrations")}
        for f in files:
            if f.name in applied:
                print(f"  applied  {f.name}")
                continue
            if args.status:
                print(f"  pending  {f.name}")
                continue
            with conn.transaction():
                conn.execute(f.read_text())
                conn.execute("insert into public.schema_migrations (name) values (%s)", (f.name,))
            print(f"  APPLIED  {f.name}")


if __name__ == "__main__":
    main()
