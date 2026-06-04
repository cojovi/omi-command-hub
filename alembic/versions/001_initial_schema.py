"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("omi_uid", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_omi_uid", "users", ["omi_uid"], unique=True)

    op.create_table(
        "omi_apps",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("omi_app_id", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("omi_uid", sa.String(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("headers", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
    )
    op.create_index("ix_webhook_events_event_type", "webhook_events", ["event_type"])
    op.create_index("ix_webhook_events_omi_uid", "webhook_events", ["omi_uid"])
    op.create_index("ix_webhook_events_status", "webhook_events", ["status"])
    op.create_index(
        "ix_webhook_events_status_received", "webhook_events", ["status", "received_at"]
    )

    op.create_table(
        "memories",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("omi_memory_id", sa.String(), nullable=True),
        sa.Column("omi_uid", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_memories_omi_memory_id", "memories", ["omi_memory_id"])
    op.create_index("ix_memories_omi_uid", "memories", ["omi_uid"])

    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("omi_uid", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("segment_hash", sa.String(), nullable=True),
        sa.Column("speaker", sa.String(), nullable=True),
        sa.Column("text", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_transcript_segments_omi_uid", "transcript_segments", ["omi_uid"])
    op.create_index("ix_transcript_segments_session_id", "transcript_segments", ["session_id"])
    op.create_index("ix_transcript_segments_segment_hash", "transcript_segments", ["segment_hash"])

    op.create_table(
        "action_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("omi_uid", sa.String(), nullable=False),
        sa.Column("source_memory_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("destination", sa.String(), nullable=True),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=False),
        sa.Column("people", postgresql.JSONB(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("omi_uid", "fingerprint", name="uq_action_items_uid_fingerprint"),
    )
    op.create_index("ix_action_items_omi_uid", "action_items", ["omi_uid"])
    op.create_index("ix_action_items_fingerprint", "action_items", ["fingerprint"])

    op.create_table(
        "notes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("omi_uid", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_notes_omi_uid", "notes", ["omi_uid"])

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("omi_uid", sa.String(), nullable=True),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("arguments", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tool_calls_omi_uid", "tool_calls", ["omi_uid"])
    op.create_index("ix_tool_calls_tool_name", "tool_calls", ["tool_name"])

    op.create_table(
        "integrations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("omi_uid", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_integrations_omi_uid", "integrations", ["omi_uid"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("rq_job_id", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "daily_summaries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("omi_uid", sa.String(), nullable=False),
        sa.Column("summary_date", sa.String(), nullable=True),
        sa.Column("headline", sa.String(), nullable=True),
        sa.Column("overview", sa.String(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_daily_summaries_omi_uid", "daily_summaries", ["omi_uid"])


def downgrade() -> None:
    for table in [
        "daily_summaries",
        "jobs",
        "integrations",
        "tool_calls",
        "notes",
        "action_items",
        "transcript_segments",
        "memories",
        "webhook_events",
        "omi_apps",
        "users",
    ]:
        op.drop_table(table)
