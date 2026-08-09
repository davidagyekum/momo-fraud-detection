"""MoMo-FDVS Flask application factory."""

from __future__ import annotations

from flask import Flask

from momo_fdvs.api.v1 import api_v1
from momo_fdvs.config import load_config
from momo_fdvs.errors import register_error_handlers
from momo_fdvs.extensions import api, cors, db, migrate
from momo_fdvs.logging import configure_logging, register_request_hooks
from momo_fdvs.seeds import register_seed_commands


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure an isolated MoMo-FDVS API instance."""
    from momo_fdvs import models as _models  # noqa: F401

    app = Flask(__name__)
    app.config.from_mapping(load_config(config_name))

    configure_logging(app)
    db.init_app(app)
    migrate.init_app(app, db, directory=app.config["MIGRATIONS_DIR"])
    api.init_app(app)
    api.register_blueprint(api_v1)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ALLOWED_ORIGINS"]}},
        supports_credentials=app.config["CORS_ALLOW_CREDENTIALS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=600,
    )
    register_request_hooks(app)
    register_error_handlers(app)
    register_seed_commands(app)
    return app


__all__ = ["create_app"]
