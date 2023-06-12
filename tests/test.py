from ..ingest import email_ingest
from ..script import qa


def test_ingest_emails_found():
    result = email_ingest("tests/test_data.csv")
    assert result is True


def test_ingest_no_new_emails():
    result = email_ingest("tests/empty_data.csv")
    assert result == "No new emails."
