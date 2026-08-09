"""Idempotent controlled-development seed command."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal

import click
from flask import Flask, current_app
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    FraudRule,
    FraudRuleSet,
    ReceiptTemplate,
    ReferenceImportBatch,
    ReferenceTransaction,
    Role,
    User,
    UserRole,
)

ROLE_DESCRIPTIONS = {
    "USER": "Receipt-submitting merchant or end user",
    "ADMIN": "System and governance administrator",
    "INVESTIGATOR": "Fraud investigation officer",
}


def _required_secret(name: str) -> str:
    value = os.getenv(name, "")
    if not value or value.startswith("CHANGE_ME") or len(value) < 12:
        raise click.ClickException(
            f"{name} must be a non-placeholder value of at least 12 characters"
        )
    return value


def _user(email_name: str, full_name_name: str, password_name: str) -> User:
    email = os.getenv(email_name, "").strip().lower()
    full_name = os.getenv(full_name_name, "").strip()
    password = _required_secret(password_name)
    if not email or not full_name:
        raise click.ClickException(f"{email_name} and {full_name_name} are required")
    existing = db.session.scalar(select(User).where(User.email == email))
    if existing is not None:
        return existing
    now = datetime.now(UTC)
    user = User(
        email=email,
        full_name=full_name,
        password_hash=generate_password_hash(password),
        status="ACTIVE",
        password_changed_at=now,
        must_change_password=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def register_seed_commands(app: Flask) -> None:
    @app.cli.command("seed-development")
    def seed_development() -> None:
        """Seed controlled local records; never runs automatically."""
        if current_app.config["ENVIRONMENT"] == "production":
            raise click.ClickException("development seeds are prohibited in production")
        for code, description in ROLE_DESCRIPTIONS.items():
            if db.session.get(Role, code) is None:
                db.session.add(Role(code=code, description=description))
        db.session.flush()

        admin = _user(
            "BOOTSTRAP_ADMIN_EMAIL", "BOOTSTRAP_ADMIN_FULL_NAME", "BOOTSTRAP_ADMIN_PASSWORD"
        )
        investigator = _user(
            "BOOTSTRAP_INVESTIGATOR_EMAIL",
            "BOOTSTRAP_INVESTIGATOR_FULL_NAME",
            "BOOTSTRAP_INVESTIGATOR_PASSWORD",
        )
        for user, role_code in ((admin, "ADMIN"), (admin, "USER"), (investigator, "INVESTIGATOR")):
            if db.session.get(UserRole, (user.id, role_code)) is None:
                db.session.add(
                    UserRole(
                        user_id=user.id,
                        role_code=role_code,
                        granted_by=None,
                        granted_at=datetime.now(UTC),
                    )
                )

        template = db.session.scalar(
            select(ReceiptTemplate).where(
                ReceiptTemplate.provider_code == "DEMO", ReceiptTemplate.version == "1.0.0"
            )
        )
        if template is None:
            db.session.add(
                ReceiptTemplate(
                    provider_code="DEMO",
                    name="Controlled demo receipt",
                    version="1.0.0",
                    status="DRAFT",
                    config={"synthetic_only": True, "anchors": []},
                    parser_version="demo-parser-1",
                    created_by=admin.id,
                    row_version=1,
                )
            )

        rule_set = db.session.scalar(select(FraudRuleSet).where(FraudRuleSet.version == "demo-1"))
        if rule_set is None:
            rule_set = FraudRuleSet(
                version="demo-1",
                status="DRAFT",
                risk_weights={"image": 0.4, "structured": 0.4, "rules": 0.2},
                thresholds={"suspicious": 35, "fraudulent": 70},
                description="Controlled development rule set",
                created_by=admin.id,
                row_version=1,
            )
            db.session.add(rule_set)
            db.session.flush()
            db.session.add(
                FraudRule(
                    rule_set_id=rule_set.id,
                    code="DEMO_AMOUNT_MISMATCH",
                    description="Controlled amount mismatch signal",
                    severity="MEDIUM",
                    condition={"field": "amount_match", "operator": "eq", "value": False},
                    score_contribution=Decimal("10.0000"),
                    reason_template="Receipt amount differs from the imported reference",
                    enabled=True,
                )
            )

        batch = db.session.scalar(
            select(ReferenceImportBatch).where(
                ReferenceImportBatch.source_label == "controlled-demo"
            )
        )
        if batch is None:
            batch = ReferenceImportBatch(
                source_label="controlled-demo",
                original_filename="controlled-demo.csv",
                file_sha256="0" * 64,
                status="COMMITTED",
                total_rows=1,
                valid_rows=1,
                invalid_rows=0,
                uploaded_by=admin.id,
                committed_at=datetime.now(UTC),
            )
            db.session.add(batch)
            db.session.flush()
            db.session.add(
                ReferenceTransaction(
                    import_batch_id=batch.id,
                    provider_code="DEMO",
                    transaction_reference="SYNTHETIC-REFERENCE-001",
                    amount=Decimal("10.00"),
                    currency="GHS",
                    source_system_id="controlled-001",
                    raw_row={"synthetic_only": True},
                )
            )
        db.session.commit()
        click.echo("Controlled development seed complete; bootstrap users must change passwords.")
