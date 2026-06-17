import pytest
from fastapi.testclient import TestClient

from api.main import app, get_backend, get_commentator
from core import db
from core.models import Base, Subscriber
from delivery import subscribers
from sqlalchemy import select


class CaptureBackend:
    name = "capture"

    def __init__(self):
        self.sent = []

    def send(self, subject, body_html, recipient):
        self.sent.append({"subject": subject, "to": recipient, "html": body_html})


# Store-level tests use the session fixture from conftest.

def test_request_subscription_creates_pending(session):
    sub, is_new = subscribers.request_subscription(session, "Reader@Example.com")
    session.commit()
    assert is_new is True
    assert sub.status == "pending"
    assert sub.email == "reader@example.com"
    assert sub.confirm_token and sub.unsubscribe_token


def test_repeat_subscription_does_not_resend(session):
    subscribers.request_subscription(session, "a@b.com")
    session.commit()
    _, is_new = subscribers.request_subscription(session, "a@b.com")
    session.commit()
    assert is_new is False


def test_confirm_then_listed(session):
    sub, _ = subscribers.request_subscription(session, "a@b.com")
    session.commit()
    subscribers.confirm(session, sub.confirm_token)
    session.commit()
    assert subscribers.confirmed_count(session) == 1


def test_unsubscribe_removes_from_confirmed(session):
    sub, _ = subscribers.request_subscription(session, "a@b.com")
    session.commit()
    subscribers.confirm(session, sub.confirm_token)
    session.commit()
    subscribers.unsubscribe(session, sub.unsubscribe_token)
    session.commit()
    assert subscribers.confirmed_count(session) == 0


def test_resubscribe_after_unsubscribe_is_new(session):
    sub, _ = subscribers.request_subscription(session, "a@b.com")
    session.commit()
    subscribers.unsubscribe(session, sub.unsubscribe_token)
    session.commit()
    _, is_new = subscribers.request_subscription(session, "a@b.com")
    session.commit()
    assert is_new is True


# Endpoint tests with a throwaway database and a capturing mail backend.

@pytest.fixture
def client(tmp_path):
    url = f"sqlite:///{tmp_path/'sub.db'}"
    engine = db.reset_engine_for_tests(url)
    Base.metadata.create_all(engine)

    backend = CaptureBackend()
    app.dependency_overrides[get_backend] = lambda: backend
    app.dependency_overrides[get_commentator] = lambda: None
    client = TestClient(app)
    client.backend = backend
    yield client
    app.dependency_overrides.clear()


def test_home_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "FinSight" in resp.text
    assert "Subscribe" in resp.text


def test_subscribe_sends_confirmation(client):
    resp = client.post("/subscribe", data={"email": "new@reader.com"})
    assert resp.status_code == 200
    assert "Check your inbox" in resp.text
    assert len(client.backend.sent) == 1
    assert client.backend.sent[0]["to"] == "new@reader.com"
    assert "confirm" in client.backend.sent[0]["html"].lower()


def test_confirm_link_activates(client):
    client.post("/subscribe", data={"email": "new@reader.com"})
    # Pull the token straight from the database to follow the link.
    session = db.get_session_factory()()
    sub = session.scalar(select(Subscriber).where(Subscriber.email == "new@reader.com"))
    token = sub.confirm_token
    session.close()

    resp = client.get(f"/confirm?token={token}")
    assert resp.status_code == 200
    assert "subscribed" in resp.text.lower()


def test_unsubscribe_link_works(client):
    client.post("/subscribe", data={"email": "new@reader.com"})
    session = db.get_session_factory()()
    sub = session.scalar(select(Subscriber).where(Subscriber.email == "new@reader.com"))
    token = sub.unsubscribe_token
    session.close()

    resp = client.get(f"/unsubscribe?token={token}")
    assert resp.status_code == 200
    assert "unsubscribed" in resp.text.lower()


def test_bad_confirm_token_is_handled(client):
    resp = client.get("/confirm?token=nope")
    assert resp.status_code == 200
    assert "not recognized" in resp.text.lower()
