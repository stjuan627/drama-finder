"""Drop legacy shot representative frame paths."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260318_0002"
down_revision = "20260317_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("shots", "representative_frame_paths")


def downgrade() -> None:
    op.add_column(
        "shots",
        sa.Column(
            "representative_frame_paths",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.alter_column("shots", "representative_frame_paths", server_default=None)
