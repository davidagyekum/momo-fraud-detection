from __future__ import annotations

import pytest

from momo_fdvs.services.verification import (
    VerificationFailure,
    _invalid_report,
    _safe_csv_cell,
    parse_reference_csv,
)

HEADER = (
    "provider_code,transaction_reference,amount,currency,sender_name,sender_phone,"
    "receiver_name,receiver_phone,occurred_at,transaction_status,source_system_id\n"
)


def test_parser_canonicalises_valid_rows_and_reports_row_errors(app) -> None:
    content = (
        HEADER + "mtn momo,abc-123,125,GHS,Demo Sender,0240000002,Demo Receiver,"
        "0240000001,2026-08-08 14:30,Successful,source-1\n"
        + "mtn momo,abc-123,bad,GH,Demo Sender,not-a-phone,,,,,source-1\n"
    ).encode()
    with app.app_context():
        result = parse_reference_csv(content)
        assert result.total_rows == 2
        assert len(result.valid_rows) == 1
        assert result.valid_rows[0].canonical == {
            "provider_code": "MTN_MOMO",
            "transaction_reference": "ABC-123",
            "amount": "125.00",
            "currency": "GHS",
            "sender_name": "DEMO SENDER",
            "sender_phone": "+233240000002",
            "receiver_name": "DEMO RECEIVER",
            "receiver_phone": "+233240000001",
            "occurred_at": "2026-08-08T14:30:00Z",
            "transaction_status": "SUCCESSFUL",
            "source_system_id": "source-1",
            "normalisation_warnings": ["TIMEZONE_INFERRED_GHANA_UTC"],
        }
        codes = {error["code"] for error in result.errors}
        assert {"INVALID_DECIMAL", "INVALID_CURRENCY", "INVALID_GHANA_PHONE"} <= codes


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "REFERENCE_FILE_EMPTY"),
        (b"provider_code,amount\nMTN,1\n", "REFERENCE_HEADERS_INVALID"),
        (
            b"provider_code,transaction_reference,amount,currency,extra\nMTN,A,1,GHS,x\n",
            "REFERENCE_HEADERS_INVALID",
        ),
        (b"\xff\xfe", "REFERENCE_FILE_ENCODING_INVALID"),
        (HEADER.encode(), "REFERENCE_FILE_EMPTY"),
        (
            b"provider_code,provider_code,transaction_reference,amount,currency\n"
            b"MTN,MTN,ABC12345,1,GHS\n",
            "REFERENCE_HEADERS_INVALID",
        ),
    ],
)
def test_parser_rejects_invalid_files(app, content: bytes, code: str) -> None:
    with app.app_context(), pytest.raises(VerificationFailure) as caught:
        parse_reference_csv(content)
    assert caught.value.code == code


def test_parser_rejects_extra_cells_and_duplicate_rows(app) -> None:
    content = (
        HEADER
        + "MTN,ABC12341,1,GHS,,,,,,,source,unexpected\n"
        + "MTN,ABC12342,2,GHS,,,,,,,source\n"
        + "MTN,ABC12342,2,GHS,,,,,,,source\n"
    ).encode()
    with app.app_context():
        result = parse_reference_csv(content)
    assert result.total_rows == 3
    assert len(result.valid_rows) == 1
    assert {error["code"] for error in result.errors} == {"MALFORMED_ROW", "DUPLICATE_ROW"}


def test_invalid_report_is_spreadsheet_formula_safe(app) -> None:
    assert _safe_csv_cell("=1+1") == "'=1+1"
    with app.app_context():
        validation = parse_reference_csv((HEADER + "MTN,A1,not-money,GHS,,,,,,,source\n").encode())
        report = _invalid_report(validation).decode()
    assert "INVALID_DECIMAL" in report
    assert "not-money" not in report
