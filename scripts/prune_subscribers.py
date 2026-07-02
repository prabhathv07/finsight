"""Prune undeliverable subscribers from the database.

An address that fails validation (a typo, or a reserved domain like
example.com) that slipped in before validation existed will bounce on every
send. This finds those rows and marks them unsubscribed so the daily briefing
stops mailing them. It reads DATABASE_URL from the environment, exactly like
the rest of the app.

    python -m scripts.prune_subscribers            # dry run: just report
    python -m scripts.prune_subscribers --apply    # actually unsubscribe them
    python -m scripts.prune_subscribers --apply --delete   # hard-delete rows

Dry run is the default so it can never surprise a production database.
"""

import argparse

from sqlalchemy import select

from core.db import session_scope
from core.models import Subscriber
from delivery.validation import is_valid_email


def find_bad(session):
    rows = session.scalars(select(Subscriber)).all()
    return [s for s in rows if not is_valid_email(s.email)]


def prune(apply=False, delete=False):
    with session_scope() as session:
        bad = find_bad(session)
        if not bad:
            print("No undeliverable subscribers found.")
            return {"found": 0, "changed": 0}

        print(f"Found {len(bad)} undeliverable address(es):")
        for s in bad:
            print(f"  - {s.email} (status={s.status})")

        if not apply:
            print("\nDry run. Re-run with --apply to unsubscribe them "
                  "(add --delete to remove the rows entirely).")
            return {"found": len(bad), "changed": 0}

        for s in bad:
            if delete:
                session.delete(s)
            else:
                s.status = "unsubscribed"
        action = "Deleted" if delete else "Unsubscribed"
        print(f"\n{action} {len(bad)} address(es).")
        return {"found": len(bad), "changed": len(bad)}


def main():
    parser = argparse.ArgumentParser(description="Prune undeliverable subscribers.")
    parser.add_argument("--apply", action="store_true", help="commit the changes")
    parser.add_argument("--delete", action="store_true",
                        help="delete rows instead of marking unsubscribed")
    args = parser.parse_args()
    prune(apply=args.apply, delete=args.delete)


if __name__ == "__main__":
    main()
