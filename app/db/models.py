import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.utcnow()


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=_uuid, primary_key=True)
    omi_uid: str = Field(unique=True, index=True)
    email: Optional[str] = None
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class OmiApp(SQLModel, table=True):
    __tablename__ = "omi_apps"

    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    omi_app_id: Optional[str] = None
    type: Optional[str] = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class WebhookEvent(SQLModel, table=True):
    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("ix_webhook_events_status_received", "status", "received_at"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    source: str = "omi"
    event_type: str = Field(index=True)
    omi_uid: Optional[str] = Field(default=None, index=True)
    raw_payload: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    headers: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    status: str = Field(default="received", index=True)
    received_at: datetime = Field(default_factory=_utcnow)
    processed_at: Optional[datetime] = None
    error: Optional[str] = None


class Memory(SQLModel, table=True):
    __tablename__ = "memories"

    id: str = Field(default_factory=_uuid, primary_key=True)
    omi_memory_id: Optional[str] = Field(default=None, index=True)
    omi_uid: Optional[str] = Field(default=None, index=True)
    title: Optional[str] = None
    summary: Optional[str] = None
    transcript: Optional[str] = Field(default=None, sa_column=Column(Text))
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    raw_payload: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_utcnow)


class TranscriptSegment(SQLModel, table=True):
    __tablename__ = "transcript_segments"

    id: str = Field(default_factory=_uuid, primary_key=True)
    omi_uid: Optional[str] = Field(default=None, index=True)
    session_id: Optional[str] = Field(default=None, index=True)
    segment_hash: Optional[str] = Field(default=None, index=True)
    speaker: Optional[str] = None
    text: Optional[str] = None
    timestamp: Optional[datetime] = None
    raw_payload: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_utcnow)


class ActionItem(SQLModel, table=True):
    __tablename__ = "action_items"
    __table_args__ = (
        UniqueConstraint("omi_uid", "fingerprint", name="uq_action_items_uid_fingerprint"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    omi_uid: str = Field(index=True)
    source_memory_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str = Field(default="open")
    due_at: Optional[datetime] = None
    destination: Optional[str] = None
    external_id: Optional[str] = None
    fingerprint: str = Field(index=True)
    priority: Optional[str] = "med"
    tags: list = Field(default_factory=list, sa_column=Column(JSONB))
    people: list = Field(default_factory=list, sa_column=Column(JSONB))
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Note(SQLModel, table=True):
    __tablename__ = "notes"

    id: str = Field(default_factory=_uuid, primary_key=True)
    omi_uid: str = Field(index=True)
    title: Optional[str] = None
    body: str
    tags: list = Field(default_factory=list, sa_column=Column(JSONB))
    source: Optional[str] = None
    external_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ToolCall(SQLModel, table=True):
    __tablename__ = "tool_calls"

    id: str = Field(default_factory=_uuid, primary_key=True)
    omi_uid: Optional[str] = Field(default=None, index=True)
    tool_name: str = Field(index=True)
    arguments: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    result: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    status: str = Field(default="pending")
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None


class Integration(SQLModel, table=True):
    __tablename__ = "integrations"

    id: str = Field(default_factory=_uuid, primary_key=True)
    omi_uid: str = Field(index=True)
    provider: str
    enabled: bool = True
    config: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class JobRecord(SQLModel, table=True):
    __tablename__ = "jobs"

    id: str = Field(default_factory=_uuid, primary_key=True)
    job_type: str
    status: str = Field(default="pending")
    payload: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    rq_job_id: Optional[str] = None
    attempts: int = 0
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class DailySummary(SQLModel, table=True):
    __tablename__ = "daily_summaries"

    id: str = Field(default_factory=_uuid, primary_key=True)
    omi_uid: str = Field(index=True)
    summary_date: Optional[str] = None
    headline: Optional[str] = None
    overview: Optional[str] = None
    raw_payload: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_utcnow)
