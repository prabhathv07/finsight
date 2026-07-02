from delivery.validation import is_valid_email, normalize_email


def test_accepts_normal_addresses():
    assert is_valid_email("reader@gmail.com")
    assert is_valid_email("a.b+tag@sub.domain.co")


def test_rejects_reserved_documentation_domain():
    assert not is_valid_email("test500@example.com")
    assert not is_valid_email("x@example.org")


def test_rejects_reserved_tlds():
    assert not is_valid_email("foo@bar.test")
    assert not is_valid_email("foo@bar.invalid")
    assert not is_valid_email("root@localhost")


def test_rejects_malformed():
    for bad in ["", "no-at", "x@y", "a b@c.com", "two@@at.com", "trailing@dot."]:
        assert not is_valid_email(bad), bad


def test_normalize_lowercases_and_strips():
    assert normalize_email("  Reader@Gmail.COM ") == "reader@gmail.com"
