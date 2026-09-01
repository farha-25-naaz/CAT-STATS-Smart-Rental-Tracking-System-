"""Seed the supervisors table with demo accounts (bcrypt-hashed PINs).

Run once after applying phase4_schema.sql:  python seed_supervisors.py
"""

from db import supabase
from security import hash_pin

DEMO_SUPERVISORS = [
    {"supervisor_id": "SUP-001", "name": "Alice Reyes", "pin": "1234"},
    {"supervisor_id": "SUP-002", "name": "Bhaskar Rao", "pin": "4321"},
    {"supervisor_id": "SUP-003", "name": "Chen Wei", "pin": "0000"},
]


def main() -> None:
    rows = [
        {
            "supervisor_id": s["supervisor_id"],
            "name": s["name"],
            "pin_hash": hash_pin(s["pin"]),
        }
        for s in DEMO_SUPERVISORS
    ]
    supabase.table("supervisors").upsert(rows, on_conflict="supervisor_id").execute()
    for s in DEMO_SUPERVISORS:
        print(f"seeded {s['supervisor_id']} ({s['name']}) pin={s['pin']}")


if __name__ == "__main__":
    main()
