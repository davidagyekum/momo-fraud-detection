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
    }
    assert "503" in paths["/api/v1/ready"]["get"]["responses"]
