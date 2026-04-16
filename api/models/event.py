import uuid
from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, ForeignKey, Index,
    Integer, String, Text, text,
)
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from api.models.base import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    _time = Column("_time", DateTime(timezone=True), nullable=False)
    sourcetype = Column(String(64), nullable=False)
    src = Column(String(128), nullable=True)
    dest = Column(String(128), nullable=True)
    user = Column("user", String(128), nullable=True)
    action = Column(String(128), nullable=True)
    severity = Column(
        String(16),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')"),
        nullable=True,
    )
    mitre_tactic = Column(String(256), nullable=True)
    bytes_out = Column(BigInteger, nullable=True)
    dest_port = Column(Integer, nullable=True)
    parse_error = Column(Boolean, default=False, server_default=text("false"))
    raw = Column(Text, nullable=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.job_id"), nullable=True)

    __table_args__ = (
        Index("idx_events_time", "_time", postgresql_ops={"_time": "DESC"}),
        Index("idx_events_sourcetype", "sourcetype"),
        Index("idx_events_action", "action"),
        Index("idx_events_severity", "severity"),
        Index(
            "idx_events_parse_error", "parse_error",
            postgresql_where=text("parse_error = TRUE"),
        ),
    )
