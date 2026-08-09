from flask import Flask


def test_allowlisted_origin_receives_cors_headers(app: Flask) -> None:
    response = app.test_client().get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_unknown_origin_receives_no_cors_permission(app: Flask) -> None:
    response = app.test_client().get(
        "/api/v1/health", headers={"Origin": "https://attacker.example"}
    )
    assert "Access-Control-Allow-Origin" not in response.headers
