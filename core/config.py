import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Runtime configuration pulled from the environment.

    Local development falls back to the Postgres instance defined in
    infra/docker-compose.yml. Nothing here should ever carry a real
    secret as a default.
    """

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://finsight:finsight@localhost:5433/finsight",
        )
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # Optional keyed fallback provider. Empty means yfinance only.
        self.polygon_api_key = os.getenv("POLYGON_API_KEY", "")

        # Email delivery. Backend is "smtp" for local Gmail or "resend" once
        # a transactional provider key is set.
        self.email_backend = os.getenv("EMAIL_BACKEND", "smtp")
        self.email_user = os.getenv("EMAIL_USER", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")
        self.email_from = os.getenv("EMAIL_FROM", os.getenv("EMAIL_USER", ""))
        self.email_to = [
            e.strip() for e in os.getenv("EMAIL_TO", "").split(",") if e.strip()
        ]
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.resend_api_key = os.getenv("RESEND_API_KEY", "")

        # Shown in the email footer to meet bulk-email requirements.
        self.mailing_address = os.getenv("MAILING_ADDRESS", "")

        # Used to build confirmation and unsubscribe links in emails.
        self.public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

        # Retrieval-augmented Q&A. Embeddings reuse the Gemini account; the
        # dimension must match the chosen embedding model and the pgvector
        # column width (text-embedding-004 -> 768).
        self.embed_model = os.getenv("EMBED_MODEL", "text-embedding-004")
        self.embed_dim = int(os.getenv("EMBED_DIM", "768"))
        self.rag_top_k = int(os.getenv("RAG_TOP_K", "5"))

        self.timezone = os.getenv("FINSIGHT_TZ", "America/Chicago")

    def has_polygon(self):
        return bool(self.polygon_api_key)


@lru_cache
def get_settings():
    return Settings()
