import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DownloadJob(Base):
    __tablename__ = "download_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    movie_title: Mapped[str] = mapped_column(String, nullable=False)
    movie_year: Mapped[int] = mapped_column(Integer, nullable=False)
    movie_id: Mapped[int] = mapped_column(Integer, nullable=False)
    torrent_url: Mapped[str] = mapped_column(Text, nullable=False)
    quality: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    speed: Mapped[str] = mapped_column(String, default="")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    discord_user_id: Mapped[str] = mapped_column(String, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
