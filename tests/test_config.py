"""Config hardening: empty env vars must behave exactly like unset ones.

GitHub Actions and Render inject undefined secrets as empty strings, so
"" slipping through as a real value is a production-only failure mode.
"""

import pytest

from core.config import Settings


def test_empty_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "")
    monkeypatch.setenv("EMAIL_BACKEND", "")
    monkeypatch.setenv("SMTP_PORT", "")
    settings = Settings()
    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.email_backend == "smtp"
    assert settings.smtp_port == 465


def test_whitespace_is_stripped(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "  AIzaExample \n")
    assert Settings().gemini_api_key == "AIzaExample"


def test_set_env_still_wins(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-exp")
    assert Settings().gemini_model == "gemini-exp"


def test_require_gemini_key_rejects_blank(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        Settings().require_gemini_key()


def test_require_gemini_key_accepts_aq_auth_key(monkeypatch):
    """AQ.-prefixed auth keys are the current Gemini key format."""
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.somekey")
    assert Settings().require_gemini_key() == "AQ.somekey"


def test_require_gemini_key_warns_on_legacy_aiza_key(monkeypatch, caplog):
    """Legacy AIza standard keys are being rejected by the API; warn loudly."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaExample123")
    with caplog.at_level("WARNING"):
        assert Settings().require_gemini_key() == "AIzaExample123"
    assert "legacy" in caplog.text
