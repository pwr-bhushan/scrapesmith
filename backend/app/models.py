"""SQLAlchemy models — the 6 tables from design plan §6."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import DateTime


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Domain(Base):
    __tablename__ = "domain"
    __table_args__ = (UniqueConstraint("host", "page_type", name="uq_domain_host_pagetype"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    host: Mapped[str] = mapped_column(Text, nullable=False)
    page_type: Mapped[str] = mapped_column(Text, nullable=False)
    render_js: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ConfigVersion(Base):
    __tablename__ = "config_version"
    __table_args__ = (UniqueConstraint("domain_id", "version", name="uq_configversion_domain_ver"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("domain.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _created_at()
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    source_file_id: Mapped[uuid.UUID | None] = mapped_column(
        # use_alter breaks the config_version <-> upload_batch <-> upload_file FK cycle (§6)
        ForeignKey("upload_file.id", use_alter=True, name="fk_cv_source_file"),
        nullable=True,
    )
    fields: Mapped[list] = mapped_column(JSONB, nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class UploadBatch(Base):
    __tablename__ = "upload_batch"

    id: Mapped[uuid.UUID] = _uuid_pk()
    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("domain.id"), nullable=False)
    config_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("config_version.id", use_alter=True, name="fk_batch_config_version"),
        nullable=True,
    )
    file_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = _created_at()


class UploadFile(Base):
    __tablename__ = "upload_file"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("upload_batch.id"), nullable=False)
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    dom_skeleton_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_html_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class ParseResult(Base):
    __tablename__ = "parse_result"

    id: Mapped[uuid.UUID] = _uuid_pk()
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("upload_file.id"), nullable=False)
    config_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("config_version.id"), nullable=False
    )
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    field_status: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = _created_at()


class Job(Base):
    __tablename__ = "job"

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("upload_batch.id"), nullable=False)
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    progress: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
