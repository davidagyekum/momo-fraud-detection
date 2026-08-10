from __future__ import annotations

import os
import uuid

import pytest
from flask import Flask
from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import FraudRuleSet, User

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="requires an isolated PostgreSQL test database",
)


def test_development_seed_creates_argon2_bootstrap_accounts_idempotently(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    suffix = uuid.uuid4()
    admin_email = f"bootstrap-admin-{suffix}@example.test"
    investigator_email = f"bootstrap-investigator-{suffix}@example.test"
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", admin_email)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_FULL_NAME", "Bootstrap Admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "Bootstrap-Admin-Password-7")
    monkeypatch.setenv("BOOTSTRAP_INVESTIGATOR_EMAIL", investigator_email)
    monkeypatch.setenv("BOOTSTRAP_INVESTIGATOR_FULL_NAME", "Bootstrap Investigator")
    monkeypatch.setenv("BOOTSTRAP_INVESTIGATOR_PASSWORD", "Bootstrap-Investigator-Password-8")

    runner = app.test_cli_runner()
    first = runner.invoke(args=["seed-development"])
    second = runner.invoke(args=["seed-development"])
    assert first.exit_code == second.exit_code == 0
    assert "Controlled development seed complete" in first.output
    with app.app_context():
        admins = list(db.session.scalars(select(User).where(User.email == admin_email)).all())
        investigators = list(
            db.session.scalars(select(User).where(User.email == investigator_email)).all()
        )
        assert len(admins) == len(investigators) == 1
        assert admins[0].password_hash.startswith("$argon2id$")
        assert admins[0].must_change_password is True
        active = db.session.scalar(select(FraudRuleSet).where(FraudRuleSet.status == "ACTIVE"))
        assert active is not None
        assert active.version == "demo-1"
