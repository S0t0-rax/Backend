"""add checklist

Revision ID: c1234567890b
Revises: b1234567890a
Create Date: 2026-06-11 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c1234567890b'
down_revision: Union[str, None] = 'b1234567890a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add checklist column to service_orders
    op.add_column('service_orders', sa.Column('checklist', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Drop checklist column from service_orders
    op.drop_column('service_orders', 'checklist')
