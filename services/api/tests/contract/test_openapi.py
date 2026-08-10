from flask import Flask

from momo_fdvs.extensions import api


def test_openapi_documents_system_routes_and_error_responses(app: Flask) -> None:
    with app.app_context():
        document = api.spec.to_dict()
    paths = document["paths"]
    assert set(paths) >= {"/api/v1/health", "/api/v1/ready", "/api/v1/version"}
    assert set(paths) >= {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/me",
        "/api/v1/me/change-password",
        "/api/v1/admin/users",
        "/api/v1/admin/users/{user_id}",
        "/api/v1/admin/users/{user_id}/roles",
        "/api/v1/admin/users/{user_id}/revoke-sessions",
        "/api/v1/transactions",
        "/api/v1/transactions/{transaction_id}/receipt",
        "/api/v1/transactions/{transaction_id}/ocr",
        "/api/v1/transactions/{transaction_id}/ocr-review",
        "/api/v1/transactions/{transaction_id}/ocr-confirmations",
        "/api/v1/transactions/{transaction_id}/analyses",
        "/api/v1/analyses/{analysis_run_id}/evidence",
    }
    assert "503" in paths["/api/v1/ready"]["get"]["responses"]
    upload = paths["/api/v1/transactions"]["post"]
    assert "multipart/form-data" in upload["requestBody"]["content"]
    assert any(
        parameter["name"] == "Idempotency-Key" and parameter["required"]
        for parameter in upload["parameters"]
    )
    assert {"400", "409", "413", "415", "429", "503"} <= set(upload["responses"])
    ocr = paths["/api/v1/transactions/{transaction_id}/ocr"]["post"]
    assert any(
        parameter["name"] == "Idempotency-Key" and parameter["required"]
        for parameter in ocr["parameters"]
    )
    assert {"400", "404", "409", "429", "503"} <= set(ocr["responses"])
    evidence = paths["/api/v1/analyses/{analysis_run_id}/evidence"]["get"]
    assert {"401", "404"} <= set(evidence["responses"])
    receipt = paths["/api/v1/transactions/{transaction_id}/receipt"]["get"]
    variant = next(
        parameter for parameter in receipt["parameters"] if parameter["name"] == "variant"
    )
    assert {"thumbnail", "original", "ela", "noise-map"} == set(variant["schema"]["enum"])
