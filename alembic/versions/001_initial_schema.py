"""empty message

Revision ID: 001_initial
Revises:
Create Date: 2026-05-13
"""

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models  # noqa: F401
    from app.database import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    import app.models  # noqa: F401
    from app.database import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
