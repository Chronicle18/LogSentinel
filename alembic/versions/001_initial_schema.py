"""Initial schema — events, jobs, sourcetype_configs

Revision ID: 001
Revises:
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- jobs table (must exist before events due to FK) ---
    op.create_table(
        "jobs",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("sourcetype", sa.String(64), nullable=True),
        sa.Column("total_lines", sa.Integer(), server_default=sa.text("0")),
        sa.Column("processed_lines", sa.Integer(), server_default=sa.text("0")),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("job_id"),
        sa.CheckConstraint("status IN ('queued', 'processing', 'complete', 'failed')"),
    )

    # --- events table ---
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sourcetype", sa.String(64), nullable=False),
        sa.Column("src", sa.String(128), nullable=True),
        sa.Column("dest", sa.String(128), nullable=True),
        sa.Column("user", sa.String(128), nullable=True),
        sa.Column("action", sa.String(128), nullable=True),
        sa.Column("severity", sa.String(16), nullable=True),
        sa.Column("mitre_tactic", sa.String(256), nullable=True),
        sa.Column("bytes_out", sa.BigInteger(), nullable=True),
        sa.Column("dest_port", sa.Integer(), nullable=True),
        sa.Column("parse_error", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("raw", sa.Text(), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.job_id"]),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')"),
    )

    # --- indexes ---
    op.create_index("idx_events_time", "events", [sa.text("_time DESC")])
    op.create_index("idx_events_sourcetype", "events", ["sourcetype"])
    op.create_index("idx_events_action", "events", ["action"])
    op.create_index("idx_events_severity", "events", ["severity"])
    op.create_index(
        "idx_events_parse_error", "events", ["parse_error"],
        postgresql_where=sa.text("parse_error = TRUE"),
    )

    # --- sourcetype_configs table ---
    op.create_table(
        "sourcetype_configs",
        sa.Column("sourcetype", sa.String(64), nullable=False),
        sa.Column("config_path", sa.Text(), nullable=False),
        sa.Column("rule_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_loaded", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("sourcetype"),
    )


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("jobs")
    op.drop_table("sourcetype_configs")
