from sqlmodel import SQLModel

# Import models so SQLModel.metadata is populated for Alembic
from app.db import models  # noqa: F401

__all__ = ["SQLModel"]
