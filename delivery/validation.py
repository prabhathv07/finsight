"""Email address validation.

A subscriber list is only as trustworthy as the addresses in it. Without a
gate at the door, a typo or a test address (test500@example.com) gets saved,
confirmed, and then mailed every day -- each send bouncing back to the sender.
This module is that gate: a basic RFC-shaped format check plus a rejection of
the reserved documentation/test domains that can never receive real mail
(RFC 2606 / RFC 6761).
"""

import re

# One @, no whitespace, and a dotted domain with a TLD. Deliberately simple:
# the goal is to catch typos and junk, not to fully parse RFC 5322.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# TLDs reserved for testing/documentation -- never route to real inboxes.
_RESERVED_TLDS = {"test", "invalid", "localhost", "example", "local"}

# Second-level documentation domains reserved by RFC 2606.
_RESERVED_DOMAINS = {"example.com", "example.net", "example.org"}


def normalize_email(email):
    return (email or "").strip().lower()


def is_valid_email(email):
    """True if the address is well-formed and not a reserved/undeliverable one."""
    email = normalize_email(email)
    if not _EMAIL_RE.match(email):
        return False

    domain = email.rsplit("@", 1)[1]
    if domain in _RESERVED_DOMAINS:
        return False
    tld = domain.rsplit(".", 1)[-1]
    if tld in _RESERVED_TLDS:
        return False
    return True
