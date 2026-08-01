"""Preserve material provenance after source deletion."""

from alembic import op
import sqlalchemy as sa


revision = "0006_material_grounding"
down_revision = "0005_provider_provenance"
branch_labels = None
depends_on = None

uuid = sa.Uuid(as_uuid=False)


def upgrade() -> None:
    op.rename_table("chapter_materials", "chapter_materials_v5")
    op.create_table(
        "chapter_materials",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("chapter_id", uuid, sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", uuid, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("source_label", sa.String(255), nullable=False),
        sa.Column("excerpts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("chapter_id", "material_id", name="uq_chapter_material"),
    )
    op.execute(
        "INSERT INTO chapter_materials "
        "(id, chapter_id, material_id, content_hash, source_label, excerpts, created_at, updated_at) "
        "SELECT id, chapter_id, material_id, content_hash, 'Historical source', '[]', created_at, updated_at "
        "FROM chapter_materials_v5"
    )
    op.drop_table("chapter_materials_v5")


def downgrade() -> None:
    pass
