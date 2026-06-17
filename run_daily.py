"""Run the daily pull and persist the results.

    python run_daily.py

Reads DATABASE_URL from the environment. Creates tables on first run so a
fresh database works without a separate migration step during phase 1.
"""

from core.db import session_scope
from core.models import create_all
from core.pipeline import run


def main():
    create_all()
    with session_scope() as session:
        result = run(session)
    print(
        f"{result['run_date']}: "
        f"{result['quotes_written']} quotes, "
        f"{result['indicators_written']} indicators"
    )


if __name__ == "__main__":
    main()
