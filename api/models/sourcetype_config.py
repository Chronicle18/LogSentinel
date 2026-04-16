from sqlalchemy import Column, DateTime, Integer, String, Text, text
from api.models.base import Base


class SourcetypeConfigModel(Base):
    __tablename__ = "sourcetype_configs"

    sourcetype = Column(String(64), primary_key=True)
    config_path = Column(Text, nullable=False)
    rule_count = Column(Integer, default=0, server_default=text("0"))
    last_loaded = Column(DateTime(timezone=True), server_default=text("now()"))
