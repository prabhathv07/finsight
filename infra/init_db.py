"""Create database tables. Safe to run repeatedly."""

from core.models import create_all

if __name__ == "__main__":
    create_all()
    print("tables ready")
