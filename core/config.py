import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _env(name, default=""):
    """Read an env var, treating empty/whitespace values as unset.

    CI and PaaS dashboards inject undefined secrets as empty strings, so a
    plain os.getenv(name, default) silently overrides the default with "".
    """
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


class Settings:
    """Runtime configuration pulled from the environment.

    Local development falls back to the Postgres instance defined in
    infra/docker-compose.yml. Nothing here should ever carry a real
    secret as a default.
    """

    def __init__(self):
        self.database_url = _env(
            "DATABASE_URL",
            "postgresql+psycopg2://finsight:finsight@localhost:5433/finsight",
        )
        self.gemini_api_key = _env("GEMINI_API_KEY")
        self.gemini_model = _env("GEMINI_MODEL", "gemini-2.5-flash")

        # Optional keyed fallback provider. Empty means yfinance only.
        self.polygon_api_key = _env("POLYGON_API_KEY")

        # Email delivery. Backend is "smtp" for local Gmail or "resend" once
        # a transactional provider key is set.
        self.email_backend = _env("EMAIL_BACKEND", "smtp")
        self.email_user = _env("EMAIL_USER")
        self.email_password = _env("EMAIL_PASSWORD")
        self.email_from = _env("EMAIL_FROM", _env("EMAIL_USER"))
        self.email_to = [
            e.strip() for e in _env("EMAIL_TO").split(",") if e.strip()
        ]
        self.smtp_host = _env("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(_env("SMTP_PORT", "465"))
        self.resend_api_key = _env("RESEND_API_KEY")
        self.brevo_api_key = _env("BREVO_API_KEY")

        # Shown in the email footer to meet bulk-email requirements.
        self.mailing_address = _env("MAILING_ADDRESS")

        # Used to build confirmation and unsubscribe links in emails.
        self.public_base_url = _env("PUBLIC_BASE_URL", "http://localhost:8000")

        # Shared secret for the privileged endpoints (/briefings/run,
        # /rag/reindex, /ask). Unset means those endpoints refuse requests.
        self.api_token = _env("FINSIGHT_API_TOKEN")

        # Retrieval-augmented Q&A. Embeddings reuse the Gemini account; the
        # dimension must match the chosen embedding model and the pgvector
        # column width (gemini-embedding-001 -> 3072).
        self.embed_model = _env("EMBED_MODEL", "gemini-embedding-001")
        self.embed_dim = int(_env("EMBED_DIM", "3072"))
        self.rag_top_k = int(_env("RAG_TOP_K", "5"))

        self.timezone = _env("FINSIGHT_TZ", "America/Chicago")

    def has_polygon(self):
        return bool(self.polygon_api_key)

    def require_gemini_key(self):
        """Fail fast, with an actionable message, when the key cannot work.

        Gemini API keys migrated from "AIza..." (standard keys) to "AQ..."
        (auth keys) in mid-2026. The API started rejecting legacy standard
        keys on 2026-06-19 with 401 ACCESS_TOKEN_TYPE_UNSUPPORTED and drops
        them entirely in September 2026, so an AIza key is the failure mode
        worth warning about; AQ. keys are the current format.
        """
        if not self.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set (or is an empty string). "
                "Set it in the environment before running."
            )
        if self.gemini_api_key.startswith("AIza"):
            import logging

            logging.getLogger("finsight.config").warning(
                "GEMINI_API_KEY is a legacy 'AIza' standard key; the Gemini "
                "API has been rejecting these since 2026-06-19. Create a new "
                "'AQ.' auth key at https://aistudio.google.com/apikey."
            )
        return self.gemini_api_key


@lru_cache
def get_settings():
    return Settings()
