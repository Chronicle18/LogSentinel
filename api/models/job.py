import uuid
from sqlalchemy import (
    CheckConstraint, Column, DateTime, Integer, String, text,
)
from sqlalchemy.dialects.postgresql import UUID
from api.models.base import Base


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    status = Column(
        String(20),
        CheckConstraint("status IN ('queued', 'processing', 'complete', 'failed')"),
        nullable=False,
        default="queued",
        server_default=text("'queued'"),
    )
    sourcetype = Column(String(64), nullable=True)
    total_lines = Column(Integer, default=0, server_default=text("0"))
    processed_lines = Column(Integer, default=0, server_default=text("0"))
    error_count = Column(Integer, default=0, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"))
