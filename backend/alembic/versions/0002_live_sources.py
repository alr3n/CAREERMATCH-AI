"""live job sources: posting URL, source platform, remove stored demo data

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16 19:30:00

* Adds ``job_listings.posting_url`` (public page of the original posting) and
  ``job_listings.source_platform`` (where it was published, e.g. "LinkedIn").
* Deletes every fictional listing created by the removed demo provider, and
  everything that referenced those listings (saved jobs, matches, feedback),
  so existing databases stop showing demo data. Child rows are deleted
  explicitly so this also works where SQLite foreign keys are off.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEMO_JOBS = "SELECT id FROM job_listings WHERE is_demo = :t OR provider = 'demo'"


def upgrade() -> None:
    with op.batch_alter_table("job_listings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("posting_url", sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column("source_platform", sa.String(length=120), nullable=True))

    bind = op.get_bind()
    params = {"t": True}
    bind.execute(
        sa.text(f"DELETE FROM match_evidence WHERE match_id IN (SELECT id FROM match_results WHERE job_id IN ({_DEMO_JOBS}))"),
        params,
    )
    bind.execute(sa.text(f"DELETE FROM user_feedback WHERE job_id IN ({_DEMO_JOBS})"), params)
    bind.execute(sa.text(f"DELETE FROM match_results WHERE job_id IN ({_DEMO_JOBS})"), params)
    bind.execute(sa.text(f"DELETE FROM saved_jobs WHERE job_id IN ({_DEMO_JOBS})"), params)
    bind.execute(sa.text(f"DELETE FROM job_skills WHERE job_id IN ({_DEMO_JOBS})"), params)
    bind.execute(sa.text(f"UPDATE job_listings SET duplicate_of_id = NULL WHERE duplicate_of_id IN ({_DEMO_JOBS})"), params)
    bind.execute(sa.text("DELETE FROM job_listings WHERE is_demo = :t OR provider = 'demo'"), params)
    bind.execute(sa.text("DELETE FROM job_sources WHERE is_demo = :t OR provider = 'demo'"), params)


def downgrade() -> None:
    # Deleted demo rows are not restored.
    with op.batch_alter_table("job_listings", schema=None) as batch_op:
        batch_op.drop_column("source_platform")
        batch_op.drop_column("posting_url")
