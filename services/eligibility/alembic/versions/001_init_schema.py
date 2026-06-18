"""Init schema: members, plans, benefits, providers, in_network, formulary, audit_log.

Revision ID: 001
Revises:
Create Date: 2026-06-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all core tables."""
    
    # PostGIS is enabled only when available, so this migration also runs on a plain
    # Postgres instance (e.g. reusing another app's DB for dev). The providers.location
    # column adapts below: geography(POINT) when PostGIS is present, else text (WKT).
    # pgvector ("vector") is intentionally deferred to the WS-4 SBC-RAG migration.
    bind = op.get_bind()
    has_postgis = bind.execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'")
    ).first() is not None
    if has_postgis:
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Create members table
    op.create_table(
        'members',
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('member_id', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('dob', sa.Date(), nullable=True),
        sa.Column('gender', sa.CHAR(1), nullable=True),
        sa.Column('plan_id', sa.Uuid(), nullable=False),
        sa.Column('enrollment_date', sa.Date(), nullable=True),
        sa.Column('eligibility_status', sa.String(), nullable=True),
        sa.Column('deductible_ytd_cents', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('oop_ytd_cents', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('audit_created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('audit_source', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('member_id'),
        sa.CheckConstraint("eligibility_status IN ('active', 'inactive', 'suspended')", name='valid_status')
    )
    op.create_index('idx_members_plan_id', 'members', ['plan_id'])
    op.create_index('idx_members_member_id', 'members', ['member_id'])

    # Create providers table with PostGIS
    op.create_table(
        'providers',
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('npi', sa.String(10), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('organization_name', sa.String(), nullable=True),
        sa.Column('credential_text', sa.String(), nullable=True),
        sa.Column('taxonomy_code', sa.String(), nullable=True),
        sa.Column('taxonomy_description', sa.String(), nullable=True),
        sa.Column('practice_location_address_line_1', sa.String(), nullable=True),
        sa.Column('practice_location_city', sa.String(), nullable=True),
        sa.Column('practice_location_state', sa.CHAR(2), nullable=True),
        sa.Column('practice_location_zip', sa.String(5), nullable=True),
        sa.Column('practice_location_phone', sa.String(), nullable=True),
        # location (PostGIS GEOGRAPHY) is added via raw SQL right after this table —
        # SQLAlchemy core has no GEOGRAPHY type and we avoid a GeoAlchemy2 dependency.
        sa.Column('accepting_new_patients', sa.Boolean(), nullable=True),
        sa.Column('quality_rating', sa.Numeric(3, 1), nullable=True),
        sa.Column('hospital_name', sa.String(), nullable=True),
        sa.Column('specialty_codes', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('audit_created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('audit_source', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('npi'),
        sa.CheckConstraint('quality_rating >= 1 AND quality_rating <= 5', name='valid_stars')
    )
    if has_postgis:
        op.execute("ALTER TABLE providers ADD COLUMN location geography(POINT, 4326)")
        op.create_index('idx_providers_location', 'providers', ['location'], postgresql_using='gist')
    else:
        # No PostGIS: store WKT as text so npi_ingest's POINT(...) insert still works.
        # Geo-distance (ST_DWithin) is unavailable until recreated on a PostGIS server.
        op.execute("ALTER TABLE providers ADD COLUMN location text")
    op.create_index('idx_providers_npi', 'providers', ['npi'])
    op.create_index('idx_providers_taxonomy', 'providers', ['specialty_codes'], postgresql_using='gin')

    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('plan_id_type', sa.String(), nullable=True),
        sa.Column('plan_marketing_name', sa.String(), nullable=False),
        sa.Column('issuer_name', sa.String(), nullable=True),
        sa.Column('plan_year', sa.SmallInteger(), nullable=True),
        sa.Column('plan_type', sa.String(), nullable=True),
        sa.Column('metal_level', sa.String(), nullable=True),
        sa.Column('hsa_eligible', sa.Boolean(), nullable=True),
        sa.Column('formulary_id', sa.String(), nullable=True),
        sa.Column('service_area_state', sa.CHAR(2), nullable=True),
        sa.Column('audit_created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('audit_source', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_marketing_name')
    )
    op.create_index('idx_plans_issuer_year', 'plans', ['issuer_name', 'plan_year'])

    # Add FK to members
    op.create_foreign_key('fk_members_plan_id', 'members', 'plans', ['plan_id'], ['id'])

    # Create plan_benefits table
    op.create_table(
        'plan_benefits',
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('plan_id', sa.Uuid(), nullable=False),
        sa.Column('benefit_name', sa.String(), nullable=True),
        sa.Column('service_category', sa.String(), nullable=True),
        sa.Column('network_type', sa.String(), nullable=True),
        sa.Column('individual_deductible_cents', sa.BigInteger(), nullable=True),
        sa.Column('family_deductible_cents', sa.BigInteger(), nullable=True),
        sa.Column('copay_amount_cents', sa.BigInteger(), nullable=True),
        sa.Column('coinsurance_percentage', sa.Numeric(3, 1), nullable=True),
        sa.Column('out_of_pocket_max_cents', sa.BigInteger(), nullable=True),
        sa.Column('benefit_description', sa.Text(), nullable=True),
        sa.Column('requires_prior_auth', sa.Boolean(), nullable=False, server_default='False'),
        sa.Column('excluded_reason', sa.Text(), nullable=True),
        sa.Column('audit_created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('audit_source', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE'),
        sa.CheckConstraint('coinsurance_percentage >= 0 AND coinsurance_percentage <= 100', 
                          name='valid_coinsurance')
    )
    op.create_index('idx_plan_benefits_plan_id', 'plan_benefits', ['plan_id'])
    op.create_index('idx_plan_benefits_category', 'plan_benefits', ['service_category'])

    # Create in_network table (sparse, heavily indexed)
    op.create_table(
        'in_network',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('plan_id', sa.Uuid(), nullable=False),
        sa.Column('provider_npi', sa.String(10), nullable=False),
        sa.Column('procedure_code', sa.String(), nullable=True),
        sa.Column('negotiated_rate_cents', sa.BigInteger(), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('bundled_codes', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('audit_created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('audit_source', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE')
    )
    op.create_index('idx_in_network_plan_npi_code', 'in_network', 
                   ['plan_id', 'provider_npi', 'procedure_code'])
    op.create_index('idx_in_network_effective', 'in_network', 
                   ['effective_date', 'expiry_date'])

    # Create formulary_drug table
    op.create_table(
        'formulary_drug',
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('plan_id', sa.Uuid(), nullable=False),
        sa.Column('drug_name', sa.String(), nullable=False),
        sa.Column('ndc_code', sa.String(), nullable=True),
        sa.Column('formulary_tier', sa.SmallInteger(), nullable=True),
        sa.Column('prior_auth_required', sa.Boolean(), nullable=False, server_default='False'),
        sa.Column('step_therapy_required', sa.Boolean(), nullable=False, server_default='False'),
        sa.Column('quantity_limit', sa.String(), nullable=True),
        sa.Column('audit_created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('audit_source', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE')
    )
    op.create_index('idx_formulary_plan_drug', 'formulary_drug', ['plan_id', 'drug_name'])
    op.create_index('idx_formulary_tier', 'formulary_drug', ['formulary_tier'])

    # Create audit_log table (immutable)
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('table_name', sa.String(), nullable=False),
        sa.Column('record_id', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('ingest_timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('data_hash', sa.String(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_source', 'audit_log', ['source', 'ingest_timestamp'])
    op.create_index('idx_audit_table', 'audit_log', ['table_name'])

    # Create ICD-10 codes table
    op.create_table(
        'icd10_codes',
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('code', sa.String(7), nullable=False),
        sa.Column('long_description', sa.Text(), nullable=True),
        sa.Column('short_description', sa.Text(), nullable=True),
        sa.Column('audit_source', sa.String(), nullable=False, server_default='cms_icd10_2026'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('idx_icd10_code', 'icd10_codes', ['code'])

    # Create HCPCS codes table
    op.create_table(
        'hcpcs_codes',
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('code', sa.String(5), nullable=False),
        sa.Column('long_description', sa.Text(), nullable=True),
        sa.Column('short_description', sa.Text(), nullable=True),
        sa.Column('audit_source', sa.String(), nullable=False, server_default='cms_hcpcs_2026'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('idx_hcpcs_code', 'hcpcs_codes', ['code'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('hcpcs_codes')
    op.drop_table('icd10_codes')
    op.drop_table('audit_log')
    op.drop_table('formulary_drug')
    op.drop_table('in_network')
    op.drop_table('plan_benefits')
    op.drop_table('members')
    op.drop_table('providers')
    op.drop_table('plans')
    op.execute("DROP EXTENSION IF EXISTS postgis")
