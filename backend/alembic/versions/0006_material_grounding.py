"""Preserve material provenance after source deletion."""

from alembic import op
import sqlalchemy as sa


revision = "0006_material_grounding"
down_revision = "0005_provider_provenance"
branch_labels = None
depends_on = None

uuid = sa.Uuid(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        "chapter_materials_v6",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("chapter_id", uuid, nullable=False),
        sa.Column("material_id", uuid, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("source_label", sa.String(255), nullable=False),
        sa.Column("excerpts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("grounding_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["chapter_id"], ["chapters.id"], name="fk_chapter_materials_v6_chapter", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("chapter_id", "material_id", name="uq_chapter_material_v6"),
    )
    op.execute(
        "INSERT INTO chapter_materials_v6 "
        "(id, chapter_id, material_id, content_hash, source_label, excerpts, grounding_applied, created_at, updated_at) "
        "SELECT links.id, links.chapter_id, links.material_id, links.content_hash, "
        "COALESCE(materials.source_filename, 'Historical source'), '[]', false, links.created_at, links.updated_at "
        "FROM chapter_materials links LEFT JOIN materials ON materials.id = links.material_id"
    )
    op.drop_table("chapter_materials")
    op.rename_table("chapter_materials_v6", "chapter_materials")


def downgrade() -> None:
    op.create_table(
        "chapter_materials_v5",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("chapter_id", uuid, nullable=False),
        sa.Column("material_id", uuid, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["chapter_id"], ["chapters.id"], name="fk_chapter_materials_v5_chapter", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["material_id"], ["materials.id"], name="fk_chapter_materials_v5_material", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("chapter_id", "material_id", name="uq_chapter_material_v5"),
    )
    op.execute(
        "INSERT INTO chapter_materials_v5 "
        "(id, chapter_id, material_id, content_hash, created_at, updated_at) "
        "SELECT links.id, links.chapter_id, links.material_id, links.content_hash, links.created_at, links.updated_at "
        "FROM chapter_materials links JOIN materials ON materials.id = links.material_id"
    )
    op.drop_table("chapter_materials")
    op.rename_table("chapter_materials_v5", "chapter_materials")
