"""Add delta timestamps, content hash, missing streak and barcode validity to products.

Revision ID: 006
Revises: 005
Create Date: 2026-10-28

"""

from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Helper to check if column exists before adding (resilient for SQLite and Postgres)
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_cols = {c['name'] for c in insp.get_columns('products')}

    if 'discovered_at' not in existing_cols:
        op.add_column('products', sa.Column('discovered_at', sa.DateTime(), nullable=True))
    if 'content_updated_at' not in existing_cols:
        op.add_column('products', sa.Column('content_updated_at', sa.DateTime(), nullable=True))
    if 'stock_updated_at' not in existing_cols:
        op.add_column('products', sa.Column('stock_updated_at', sa.DateTime(), nullable=True))
    if 'last_seen_at' not in existing_cols:
        op.add_column('products', sa.Column('last_seen_at', sa.DateTime(), nullable=True))
    if 'missing_streak' not in existing_cols:
        op.add_column('products', sa.Column('missing_streak', sa.Integer(), nullable=False, server_default='0'))
    if 'content_hash' not in existing_cols:
        op.add_column('products', sa.Column('content_hash', sa.String(length=64), nullable=True))
    if 'ean_valid' not in existing_cols:
        op.add_column('products', sa.Column('ean_valid', sa.Boolean(), nullable=True))
    if 'ean_error' not in existing_cols:
        op.add_column('products', sa.Column('ean_error', sa.String(length=200), nullable=True))

    # Backfill default timestamp values from created_at/updated_at
    op.execute(
        sa.text(
            "UPDATE products SET "
            "discovered_at = COALESCE(discovered_at, created_at), "
            "content_updated_at = COALESCE(content_updated_at, updated_at, created_at), "
            "stock_updated_at = COALESCE(stock_updated_at, updated_at, created_at), "
            "last_seen_at = COALESCE(last_seen_at, updated_at, created_at) "
            "WHERE discovered_at IS NULL OR content_updated_at IS NULL"
        )
    )

    # Indices
    existing_indices = {idx['name'] for idx in insp.get_indexes('products')}
    if 'idx_products_content_updated' not in existing_indices:
        op.create_index('idx_products_content_updated', 'products', ['content_updated_at'], unique=False)
    if 'idx_products_stock_updated' not in existing_indices:
        op.create_index('idx_products_stock_updated', 'products', ['stock_updated_at'], unique=False)
    if 'idx_products_last_seen' not in existing_indices:
        op.create_index('idx_products_last_seen', 'products', ['last_seen_at'], unique=False)


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_indices = {idx['name'] for idx in insp.get_indexes('products')}

    if 'idx_products_last_seen' in existing_indices:
        op.drop_index('idx_products_last_seen', table_name='products')
    if 'idx_products_stock_updated' in existing_indices:
        op.drop_index('idx_products_stock_updated', table_name='products')
    if 'idx_products_content_updated' in existing_indices:
        op.drop_index('idx_products_content_updated', table_name='products')

    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_column('ean_error')
        batch_op.drop_column('ean_valid')
        batch_op.drop_column('content_hash')
        batch_op.drop_column('missing_streak')
        batch_op.drop_column('last_seen_at')
        batch_op.drop_column('stock_updated_at')
        batch_op.drop_column('content_updated_at')
        batch_op.drop_column('discovered_at')
