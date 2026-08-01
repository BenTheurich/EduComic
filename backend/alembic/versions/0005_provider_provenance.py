"""Mark pre-corrected provider-input provenance conservatively incomplete."""

from alembic import op
import sqlalchemy as sa


revision = "0005_provider_provenance"
down_revision = "0004_review_fixes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE generation_runs SET settings_snapshot = json_set("
            "COALESCE(settings_snapshot, '{}'), '$.provenance_complete', json('false'))"
        )
    )


def downgrade() -> None:
    pass
