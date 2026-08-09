"""Unbound Flask extensions initialised by the application factory."""

from flask_cors import CORS
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base reserved for the P02 domain schema."""


db = SQLAlchemy(model_class=Base, session_options={"expire_on_commit": False})
migrate = Migrate(compare_type=True, render_as_batch=False)
api = Api()
cors = CORS()
