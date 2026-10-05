"""Add stock_update_logs table for tracking stock quantity and status changes.

Revision ID: 005
Revises: 004
Create Date: 2026-10-05

"""

from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'stock_update_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sku', sa.String(length=200), nullable=False),
        sa.Column('title', sa.String(length=1000), nullable=True),
        sa.Column('old_stock', sa.Integer(), nullable=True),
        sa.Column('new_stock', sa.Integer(), nullable=True),
        sa.Column('old_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=True),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('scrape_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_stock_logs_product', 'stock_update_logs', ['product_id'], unique=False)
    op.create_index('idx_stock_logs_sku', 'stock_update_logs', ['sku'], unique=False)
    op.create_index('idx_stock_logs_created', 'stock_update_logs', ['created_at'], unique=False)


def downgrade():
    op.drop_index('idx_stock_logs_created', table_name='stock_update_logs')
    op.drop_index('idx_stock_logs_sku', table_name='stock_update_logs')
    op.drop_index('idx_stock_logs_product', table_name='stock_update_logs')
    op.drop_table('stock_update_logs')
