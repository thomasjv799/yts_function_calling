import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from db.models import Base, DownloadJob
from config import Config

engine = create_async_engine(Config.async_db_url())
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def add_job(
    movie_title: str,
    movie_year: int,
    movie_id: int,
    torrent_url: str,
    quality: str,
    discord_user_id: str,
) -> DownloadJob:
    async with AsyncSessionLocal() as session:
        job = DownloadJob(
            movie_title=movie_title,
            movie_year=movie_year,
            movie_id=movie_id,
            torrent_url=torrent_url,
            quality=quality,
            discord_user_id=discord_user_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


async def get_pending_job() -> DownloadJob | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DownloadJob)
            .where(DownloadJob.status == "pending")
            .order_by(DownloadJob.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()


async def update_job(job_id: uuid.UUID, **kwargs) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(DownloadJob).where(DownloadJob.id == job_id))
        job = result.scalar_one()
        for key, value in kwargs.items():
            setattr(job, key, value)
        await session.commit()


async def get_all_jobs(limit: int = 20) -> list[DownloadJob]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DownloadJob).order_by(DownloadJob.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


async def cancel_job_by_title(movie_title: str) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DownloadJob)
            .where(DownloadJob.movie_title.ilike(f"%{movie_title}%"))
            .where(DownloadJob.status == "pending")
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if not job:
            return False
        job.status = "cancelled"
        await session.commit()
        return True


async def check_duplicate(movie_title: str, movie_year: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DownloadJob)
            .where(DownloadJob.movie_title.ilike(f"%{movie_title}%"))
            .where(DownloadJob.movie_year == movie_year)
            .where(DownloadJob.status.in_(["pending", "downloading", "done"]))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
