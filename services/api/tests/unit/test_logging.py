from momo_fdvs.logging import redact


def test_redacts_nested_sensitive_fields() -> None:
    payload = {
        "email": "demo@example.test",
        "password": "not-for-logs",
        "nested": [{"authorization": "Bearer private"}],
    }
    assert redact(payload) == {
        "email": "demo@example.test",
        "password": "[REDACTED]",
        "nested": [{"authorization": "[REDACTED]"}],
    }
