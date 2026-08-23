"""Version-one system routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import current_app, g
from flask.views import MethodView
from flask_smorest import Blueprint

from momo_fdvs.api.v1.schemas import (
    HealthEnvelopeSchema,
    ReadinessEnvelopeSchema,
    VersionEnvelopeSchema,
)
from momo_fdvs.readiness import probe_readiness
from momo_fdvs.services.hybrid_text_risk import HYBRID_RULESET_VERSION
from momo_fdvs.services.risk_policy import load_risk_policy

_RISK_POLICY_PATH = (
    Path(__file__).resolve().parents[2] / "policies" / "risk_policy_demo_v1.json"
)

api_v1 = Blueprint(
    "api-v1",
    __name__,
    url_prefix="/api/v1",
    description="Versioned MoMo-FDVS API",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


@api_v1.route("/health")
class HealthResource(MethodView):
    @api_v1.response(200, HealthEnvelopeSchema)
    def get(self) -> dict[str, Any]:
        """Return process liveness without probing dependencies."""
        return {
            "data": {
                "status": "ok",
                "service": "momo-fdvs-api",
                "version": current_app.config["APP_VERSION"],
            },
            "meta": _meta(),
        }


@api_v1.route("/ready")
class ReadinessResource(MethodView):
    @api_v1.alt_response(
        503,
        schema=ReadinessEnvelopeSchema,
        description="A core dependency is unavailable.",
    )
    @api_v1.response(200, ReadinessEnvelopeSchema)
    def get(self) -> tuple[dict[str, Any], int]:
        """Return a safe core and analysis dependency matrix."""
        result = probe_readiness()
        return {"data": result.as_dict(), "meta": _meta()}, 200 if result.ready else 503


@api_v1.route("/version")
class VersionResource(MethodView):
    @api_v1.response(200, VersionEnvelopeSchema)
    def get(self) -> dict[str, Any]:
        """Return non-sensitive application and API contract versions."""
        return {
            "data": {
                "application": "momo-fdvs-api",
                "version": current_app.config["APP_VERSION"],
                "build_commit": current_app.config["APP_BUILD_SHA"],
                "api_contract_version": current_app.config["API_CONTRACT_VERSION"],
                "ocr_pipeline_version": current_app.config["OCR_PIPELINE_VERSION"],
                "fraud_ruleset_version": HYBRID_RULESET_VERSION,
                "risk_policy_version": load_risk_policy(
                    _RISK_POLICY_PATH
                ).policy_version,
            },
            "meta": _meta(),
        }


__all__ = ["api_v1"]
