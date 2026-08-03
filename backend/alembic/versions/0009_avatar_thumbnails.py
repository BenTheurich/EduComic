"""Store locally derived compact avatar thumbnails."""

from alembic import op
import sqlalchemy as sa


revision = "0009_avatar_thumbnails"
down_revision = "0008_panel_regeneration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("students", sa.Column("avatar_thumbnail_object_path", sa.String(500)))


def downgrade() -> None:
    op.drop_column("students", "avatar_thumbnail_object_path")
