"""Esquema inicial: users, cases, data_sources, subtasks, findings, etc.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-16
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="analyst"),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("priority", sa.SmallInteger, nullable=False, server_default="3"),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "total_subtasks", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "completed_subtasks", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "failed_subtasks", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("report_storage_key", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_owner_id", "cases", ["owner_id"])

    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_data_sources_case_id", "data_sources", ["case_id"])

    op.create_table(
        "subtasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "data_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_sources.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("worker_type", sa.String(32), nullable=False),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="pending"
        ),
        sa.Column("attempts", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("priority", sa.SmallInteger, nullable=False, server_default="3"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_subtasks_case_id", "subtasks", ["case_id"])
    op.create_index("ix_subtasks_status", "subtasks", ["status"])
    op.create_index("ix_subtasks_worker_type", "subtasks", ["worker_type"])

    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subtask_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subtasks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("severity", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_findings_case_id", "findings", ["case_id"])
    op.create_index("ix_findings_category", "findings", ["category"])
    op.create_index("ix_findings_severity", "findings", ["severity"])

    op.create_table(
        "case_state_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("reason", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_case_state_history_case_id", "case_state_history", ["case_id"]
    )

    op.create_table(
        "processed_tasks",
        sa.Column("task_id", sa.String(128), primary_key=True),
        sa.Column(
            "subtask_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("worker_type", sa.String(32), nullable=False),
        sa.Column("result_summary", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("processed_tasks")
    op.drop_index("ix_case_state_history_case_id", table_name="case_state_history")
    op.drop_table("case_state_history")
    op.drop_index("ix_findings_severity", table_name="findings")
    op.drop_index("ix_findings_category", table_name="findings")
    op.drop_index("ix_findings_case_id", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_subtasks_worker_type", table_name="subtasks")
    op.drop_index("ix_subtasks_status", table_name="subtasks")
    op.drop_index("ix_subtasks_case_id", table_name="subtasks")
    op.drop_table("subtasks")
    op.drop_index("ix_data_sources_case_id", table_name="data_sources")
    op.drop_table("data_sources")
    op.drop_index("ix_cases_owner_id", table_name="cases")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_table("cases")
    op.drop_table("users")
