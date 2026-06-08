"""add multi tenancy

Revision ID: b1234567890a
Revises: a571f28b1234
Create Date: 2026-06-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = 'b1234567890a'
down_revision: Union[str, None] = 'a571f28b1234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear tabla tenants
    op.create_table(
        'tenants',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('tax_id', sa.String(length=50), nullable=True),
        sa.Column('subdomain', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subdomain'),
        sa.UniqueConstraint('tax_id')
    )

    # 2. Agregar tenant_id a las tablas
    op.add_column('users', sa.Column('tenant_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_users_tenant_id', 'users', 'tenants', ['tenant_id'], ['id'], ondelete='SET NULL')

    op.add_column('workshops', sa.Column('tenant_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_workshops_tenant_id', 'workshops', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    op.add_column('incidents', sa.Column('tenant_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_incidents_tenant_id', 'incidents', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    # 3. Data Migration (Crear Tenant por cada Dueño y asignar dependencias)
    connection = op.get_bind()
    
    # Obtener usuarios que son dueños (rol 'workshop_owner')
    owners_result = connection.execute(text("""
        SELECT u.id, u.full_name 
        FROM users u
        JOIN user_roles ur ON u.id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        WHERE r.name = 'workshop_owner'
    """)).fetchall()

    for owner in owners_result:
        owner_id = owner[0]
        owner_name = owner[1]

        # Crear un Tenant para este dueño
        tenant_name = f"Taller de {owner_name}"
        result = connection.execute(text(
            "INSERT INTO tenants (name) VALUES (:name) RETURNING id"
        ), {"name": tenant_name})
        tenant_id = result.scalar()

        # Asignar tenant_id al dueño
        connection.execute(text(
            "UPDATE users SET tenant_id = :tenant_id WHERE id = :owner_id"
        ), {"tenant_id": tenant_id, "owner_id": owner_id})

        # Asignar tenant_id a los mecánicos (empleados de este dueño)
        connection.execute(text(
            "UPDATE users SET tenant_id = :tenant_id WHERE employer_id = :owner_id"
        ), {"tenant_id": tenant_id, "owner_id": owner_id})

        # Asignar tenant_id a los talleres del dueño
        connection.execute(text(
            "UPDATE workshops SET tenant_id = :tenant_id WHERE owner_id = :owner_id"
        ), {"tenant_id": tenant_id, "owner_id": owner_id})

        # Asignar tenant_id a los incidentes atendidos por mecánicos de este dueño
        connection.execute(text("""
            UPDATE incidents 
            SET tenant_id = :tenant_id 
            WHERE id IN (
                SELECT so.incident_id 
                FROM service_orders so 
                JOIN users mech ON so.mechanic_id = mech.id
                WHERE mech.employer_id = :owner_id OR mech.id = :owner_id
            )
        """), {"tenant_id": tenant_id, "owner_id": owner_id})


def downgrade() -> None:
    # Revertir todo
    op.drop_constraint('fk_incidents_tenant_id', 'incidents', type_='foreignkey')
    op.drop_column('incidents', 'tenant_id')

    op.drop_constraint('fk_workshops_tenant_id', 'workshops', type_='foreignkey')
    op.drop_column('workshops', 'tenant_id')

    op.drop_constraint('fk_users_tenant_id', 'users', type_='foreignkey')
    op.drop_column('users', 'tenant_id')

    op.drop_table('tenants')
