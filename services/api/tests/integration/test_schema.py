from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from tests.factories import create_complete_graph

from momo_fdvs.extensions import db
from momo_fdvs.models import AnalysisStageRun, AuditLog, User

pytestmark = pytest.mark.skipif(
    not (os.getenv("TEST_DATABASE_URL") or os.getenv("P02_TEST_DATABASE_URL")),
    reason="requires an isolated PostgreSQL test database",
)


def test_migration_exposes_complete_schema(app) -> None:
    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())
    assert len(tables) == 31  # 30 domain tables plus alembic_version
    assert {"users", "receipts", "analysis_runs", "verification_results", "audit_logs"} <= tables


def test_complete_factory_graph_and_case_insensitive_email_uniqueness(app) -> None:
    with app.app_context():
        create_complete_graph(db.session)
        db.session.flush()
        existing = db.session.scalar(select(User).limit(1))
        assert existing is not None
        db.session.add(
            User(
                email=existing.email.upper(),
                password_hash="fixture",
                full_name="Duplicate",
                status="ACTIVE",
                password_changed_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()

        graph = create_complete_graph(db.session)
        db.session.commit()
        audit = graph["audit"]
        assert isinstance(audit, AuditLog)
        audit.action = "tampered"
        with pytest.raises(DBAPIError):
            db.session.commit()
        db.session.rollback()


def test_invalid_state_and_audit_mutation_are_rejected(app) -> None:
    with app.app_context():
        invalid = User(
            email="invalid@example.test",
            password_hash="fixture",
            full_name="Invalid",
            status="UNKNOWN",
            password_changed_at=datetime.now(UTC),
        )
        db.session.add(invalid)
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


def test_terminal_analysis_and_stage_evidence_are_immutable(app) -> None:
    with app.app_context():
        graph = create_complete_graph(db.session)
        run = graph["run"]
        run.status = "COMPLETED"
        stage = AnalysisStageRun(
            analysis_run_id=run.id,
            stage="FINALIZE",
            status="COMPLETED",
            attempt=1,
            details={"controlled": True},
        )
        db.session.add(stage)
        db.session.commit()

        run.error_code = "MUTATED"
        with pytest.raises(DBAPIError):
            db.session.commit()
        db.session.rollback()

        stage.details = {"controlled": False}
        with pytest.raises(DBAPIError):
            db.session.commit()
        db.session.rollback()
