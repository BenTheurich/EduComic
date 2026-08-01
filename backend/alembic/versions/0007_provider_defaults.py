"""Move local settings to the current OpenAI default without changing run provenance."""

from alembic import op
import sqlalchemy as sa


revision = "0007_provider_defaults"
down_revision = "0006_material_grounding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text("UPDATE settings SET openai_model = 'gpt-5.6-terra' WHERE openai_model = 'gpt-5.1'")
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("UPDATE settings SET openai_model = 'gpt-5.1' WHERE openai_model = 'gpt-5.6-terra'")
    )
