from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(120))
    tech_stack: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending | in_progress | completed | adapted
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="Milestone.id",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    timeline_bucket: Mapped[str] = mapped_column(
        String(10)
    )  # '30_day' | '60_day' | '90_day'
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending | in_progress | completed | adapted
    description: Mapped[str] = mapped_column(Text, default="")
    dependencies: Mapped[list] = mapped_column(JSON, default=list)

    workflow: Mapped[Workflow] = relationship(back_populates="milestones")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    action_type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workflow: Mapped[Workflow] = relationship(back_populates="audit_logs")
