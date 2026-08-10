"""MoMo-FDVS Flask application factory."""

from __future__ import annotations

from flask import Flask

from momo_fdvs.api.v1 import api_v1
from momo_fdvs.api.v1.admin_users import admin_users_blueprint
from momo_fdvs.api.v1.analyses import analyses_blueprint
from momo_fdvs.api.v1.auth import auth_blueprint, identity_blueprint
from momo_fdvs.api.v1.ocr import ocr_blueprint
from momo_fdvs.api.v1.reference_imports import (
    reference_imports_blueprint,
    reference_transactions_blueprint,
)
from momo_fdvs.api.v1.transactions import transactions_blueprint
from momo_fdvs.config import load_config
from momo_fdvs.errors import register_error_handlers
from momo_fdvs.extensions import api, cors, db, limiter, migrate
from momo_fdvs.logging import configure_logging, register_request_hooks
from momo_fdvs.seeds import register_seed_commands
from momo_fdvs.storage import create_storage


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure an isolated MoMo-FDVS API instance."""
    from momo_fdvs import models as _models  # noqa: F401

    app = Flask(__name__)
    app.config.from_mapping(load_config(config_name))
    app.extensions["object_storage"] = create_storage(app)

    configure_logging(app)
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db, directory=app.config["MIGRATIONS_DIR"])
    api.init_app(app)
    api.register_blueprint(api_v1)
    api.register_blueprint(auth_blueprint)
    api.register_blueprint(identity_blueprint)
    api.register_blueprint(admin_users_blueprint)
    api.register_blueprint(analyses_blueprint)
    api.register_blueprint(transactions_blueprint)
    api.register_blueprint(ocr_blueprint)
    api.register_blueprint(reference_imports_blueprint)
    api.register_blueprint(reference_transactions_blueprint)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ALLOWED_ORIGINS"]}},
        supports_credentials=app.config["CORS_ALLOW_CREDENTIALS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "Idempotency-Key",
            "X-CSRF-Token",
            "X-Client-Type",
        ],
        expose_headers=["X-Request-ID"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=600,
    )
    register_request_hooks(app)
    register_error_handlers(app)
    register_seed_commands(app)
    return app


__all__ = ["create_app"]
