"""Persistence for uploads: get-or-create domain, write files to disk, insert rows.

Files land at ./uploads/{batch_id}/{index}_{safe_filename}; the numeric prefix is the stable
per-batch file index used by the render endpoint (avoids depending on DB row order).
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConfigVersion, Domain, UploadBatch, UploadFile
from app.skeleton import dom_skeleton_hash

UPLOADS_DIR = Path("uploads")


def _index_of(path: str) -> int:
    try:
        return int(Path(path).name.split("_", 1)[0])
    except (ValueError, IndexError):
        return 0


async def get_or_create_domain(
    session: AsyncSession, host: str, page_type: str, render_js: bool
) -> Domain:
    existing = (
        await session.execute(
            select(Domain).where(Domain.host == host, Domain.page_type == page_type)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    domain = Domain(host=host, page_type=page_type, render_js=render_js)
    session.add(domain)
    await session.flush()
    return domain


async def create_batch_with_files(
    session: AsyncSession, domain: Domain, files: list
) -> UploadBatch:
    batch = UploadBatch(domain_id=domain.id, file_count=len(files), status="pending")
    session.add(batch)
    await session.flush()

    batch_dir = UPLOADS_DIR / str(batch.id)
    batch_dir.mkdir(parents=True, exist_ok=True)
    for index, (name, data) in enumerate(files):
        path = batch_dir / f"{index}_{name}"
        path.write_bytes(data)
        html = data.decode("utf-8", errors="replace")
        session.add(
            UploadFile(
                batch_id=batch.id,
                filename=name,
                sha256=hashlib.sha256(data).hexdigest(),
                dom_skeleton_hash=dom_skeleton_hash(html),
                raw_html_path=str(path),
            )
        )
    await session.flush()
    return batch


async def list_batch_files(session: AsyncSession, batch_id: uuid.UUID) -> list:
    rows = (
        await session.execute(select(UploadFile).where(UploadFile.batch_id == batch_id))
    ).scalars().all()
    return sorted(rows, key=lambda f: _index_of(f.raw_html_path))


async def file_at_index(
    session: AsyncSession, batch_id: uuid.UUID, index: int
) -> Optional[UploadFile]:
    for f in await list_batch_files(session, batch_id):
        if _index_of(f.raw_html_path) == index:
            return f
    return None


async def create_config_version(
    session: AsyncSession,
    domain_id: uuid.UUID,
    fields: list,
    created_by: str = "user",
    source_file_id: Optional[uuid.UUID] = None,
) -> ConfigVersion:
    """Insert the next config version for a domain, computing version under a per-domain advisory
    lock (§11) so concurrent heals/saves serialize instead of colliding on the unique constraint."""
    # xact-scoped advisory lock keyed on the domain uuid text; released at commit/rollback
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:d))"), {"d": str(domain_id)}
    )
    current_max = (
        await session.execute(
            select(func.max(ConfigVersion.version)).where(ConfigVersion.domain_id == domain_id)
        )
    ).scalar()
    version = (current_max or 0) + 1
    cv = ConfigVersion(
        domain_id=domain_id,
        version=version,
        fields=fields,
        created_by=created_by,
        source_file_id=source_file_id,
        parent_version=current_max,
    )
    session.add(cv)
    await session.flush()
    return cv


async def latest_config_version(
    session: AsyncSession, domain_id: uuid.UUID
) -> Optional[ConfigVersion]:
    return (
        await session.execute(
            select(ConfigVersion)
            .where(ConfigVersion.domain_id == domain_id)
            .order_by(ConfigVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def list_config_versions(session: AsyncSession, domain_id: uuid.UUID) -> list:
    return list(
        (
            await session.execute(
                select(ConfigVersion)
                .where(ConfigVersion.domain_id == domain_id)
                .order_by(ConfigVersion.version.asc())
            )
        ).scalars()
    )


async def effective_config_version(session: AsyncSession, batch) -> Optional[ConfigVersion]:
    """The config a batch runs against: pinned version if set, else the domain's latest (§11)."""
    if batch.config_version_id is not None:
        cv = await session.get(ConfigVersion, batch.config_version_id)
        if cv is not None:
            return cv
    return await latest_config_version(session, batch.domain_id)


async def config_version_at(
    session: AsyncSession, domain_id: uuid.UUID, version: int
) -> Optional[ConfigVersion]:
    return (
        await session.execute(
            select(ConfigVersion).where(
                ConfigVersion.domain_id == domain_id, ConfigVersion.version == version
            )
        )
    ).scalar_one_or_none()
