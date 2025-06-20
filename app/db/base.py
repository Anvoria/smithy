import re
import uuid
from datetime import datetime, UTC

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    Provides common fields such as ID, created_at, and updated_at.
    """

    @declared_attr
    def __tablename__(cls) -> str:
        """
        Automatically generate the table name based on the class name.
        Converts CamelCase to snake_case.
        """
        name = cls.__name__
        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        if snake_case.endswith("y") and snake_case[-2] not in "aeiou":
            return snake_case[:-1] + "ies"
        elif snake_case.endswith(("s", "x", "z", "ch", "sh")):
            return snake_case + "es"
        else:
            return snake_case + "s"

    # Primary key ID field
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
