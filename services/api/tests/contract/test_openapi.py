from flask import Flask

from momo_fdvs.extensions import api


def test_openapi_documents_system_routes_and_error_responses(app: Flask) -> None:
    with app.app_context():
        document = api.spec.to_dict()
    paths = document["paths"]
    assert set(paths) >= {"/api/v1/health", "/api/v1/ready", "/api/v1/version"}
    assert "503" in paths["/api/v1/ready"]["get"]["responses"]
