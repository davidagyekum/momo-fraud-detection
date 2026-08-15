"""Explicit administrator CLI for governed model registry operations."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import click
from flask import Flask
from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import User
from momo_fdvs.policies.auth import user_roles
from momo_fdvs.services.model_registry import (
    ModelRegistryFailure,
    activate_image_model,
    activate_structured_model,
    register_image_model,
    register_structured_model,
)


def _actor(email: str) -> tuple[User, set[str]]:
    actor = db.session.scalar(select(User).where(User.email == email.strip().lower()))
    if actor is None:
        raise click.ClickException("The administrator account was not found.")
    return actor, user_roles(actor.id)


def _payload(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > 1_048_576:
        raise click.ClickException("The registry payload is missing or too large.")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise click.ClickException("The registry payload is not valid JSON.") from exc
    if not isinstance(loaded, dict):
        raise click.ClickException("The registry payload must be a JSON object.")
    return loaded


def register_model_commands(app: Flask) -> None:
    @app.cli.command("model-register-structured")
    @click.option("--payload", "payload_path", type=click.Path(path_type=Path), required=True)
    @click.option("--actor-email", required=True)
    def register_command(payload_path: Path, actor_email: str) -> None:
        """Register a locally present, hash-verified structured model artifact."""

        actor, roles = _actor(actor_email)
        try:
            model = register_structured_model(_payload(payload_path), actor, roles)
        except ModelRegistryFailure as exc:
            raise click.ClickException(f"{exc.code}: {exc}") from exc
        click.echo(f"registered {model.id} status={model.status}")

    @app.cli.command("model-activate-structured")
    @click.option("--model-id", type=click.UUID, required=True)
    @click.option("--actor-email", required=True)
    @click.option("--confirm", is_flag=True, help="Confirm the evidential activation.")
    def activate_command(model_id: uuid.UUID, actor_email: str, confirm: bool) -> None:
        """Activate one READY structured model after artifact re-verification."""

        actor, roles = _actor(actor_email)
        try:
            model = activate_structured_model(
                model_id, actor, roles, confirmed=confirm, rollback=False
            )
        except ModelRegistryFailure as exc:
            raise click.ClickException(f"{exc.code}: {exc}") from exc
        click.echo(f"activated {model.id} version={model.version}")

    @app.cli.command("model-rollback-structured")
    @click.option("--model-id", type=click.UUID, required=True)
    @click.option("--actor-email", required=True)
    @click.option("--confirm", is_flag=True, help="Confirm the evidential rollback.")
    def rollback_command(model_id: uuid.UUID, actor_email: str, confirm: bool) -> None:
        """Rollback to one RETIRED structured model after re-verification."""

        actor, roles = _actor(actor_email)
        try:
            model = activate_structured_model(
                model_id, actor, roles, confirmed=confirm, rollback=True
            )
        except ModelRegistryFailure as exc:
            raise click.ClickException(f"{exc.code}: {exc}") from exc
        click.echo(f"rolled back {model.id} version={model.version}")

    @app.cli.command("model-register-image")
    @click.option("--payload", "payload_path", type=click.Path(path_type=Path), required=True)
    @click.option("--actor-email", required=True)
    def register_image_command(payload_path: Path, actor_email: str) -> None:
        """Register a locally present, hash-verified Keras image artifact."""

        actor, roles = _actor(actor_email)
        try:
            model = register_image_model(_payload(payload_path), actor, roles)
        except ModelRegistryFailure as exc:
            raise click.ClickException(f"{exc.code}: {exc}") from exc
        click.echo(f"registered {model.id} status={model.status}")

    @app.cli.command("model-activate-image")
    @click.option("--model-id", type=click.UUID, required=True)
    @click.option("--actor-email", required=True)
    @click.option("--confirm", is_flag=True, help="Confirm the evidential activation.")
    def activate_image_command(model_id: uuid.UUID, actor_email: str, confirm: bool) -> None:
        """Activate one READY image model after artifact re-verification."""

        actor, roles = _actor(actor_email)
        try:
            model = activate_image_model(model_id, actor, roles, confirmed=confirm)
        except ModelRegistryFailure as exc:
            raise click.ClickException(f"{exc.code}: {exc}") from exc
        click.echo(f"activated {model.id} version={model.version}")

    @app.cli.command("model-rollback-image")
    @click.option("--model-id", type=click.UUID, required=True)
    @click.option("--actor-email", required=True)
    @click.option("--confirm", is_flag=True, help="Confirm the evidential rollback.")
    def rollback_image_command(model_id: uuid.UUID, actor_email: str, confirm: bool) -> None:
        """Rollback to one RETIRED image model after artifact re-verification."""

        actor, roles = _actor(actor_email)
        try:
            model = activate_image_model(model_id, actor, roles, confirmed=confirm, rollback=True)
        except ModelRegistryFailure as exc:
            raise click.ClickException(f"{exc.code}: {exc}") from exc
        click.echo(f"rolled back {model.id} version={model.version}")
