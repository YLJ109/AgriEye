"""ORM 数据模型 - 用户、诊断记录、地块档案、农事提醒。"""
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openid: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    password: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[str] = mapped_column(String(16), default="user")
    nickname: Mapped[str] = mapped_column(String(64), default="农户")
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)  # 所在地区
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    plots: Mapped[list["Plot"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plot_id: Mapped[int | None] = mapped_column(ForeignKey("plots.id"), nullable=True)

    image_path: Mapped[str] = mapped_column(String(255))
    coarse_category: Mapped[str] = mapped_column(String(32), index=True)  # 四大类
    fine_class: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 细分
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(16), default="moderate")  # mild/moderate/severe

    # 识别详情与治理方案（JSON）
    detection_boxes: Mapped[list] = mapped_column(JSON, default=list)
    scheme: Mapped[dict] = mapped_column(JSON, default=dict)  # 治理方案
    rag_advice: Mapped[str | None] = mapped_column(Text, nullable=True)  # RAG 建议

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="diagnoses")
    plot: Mapped["Plot | None"] = relationship(back_populates="diagnoses")


class Plot(Base):
    """地块长势档案。"""
    __tablename__ = "plots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))  # 地块名称
    crop: Mapped[str] = mapped_column(String(32))  # 作物
    area_mu: Mapped[float] = mapped_column(Float, default=0.0)  # 面积（亩）
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    growth_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="plots")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="plot")


class FarmingReminder(Base):
    """农事提醒 / 节气种植建议。"""
    __tablename__ = "farming_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    solar_term: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 节气
    crop: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1低 2中 3高
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    remind_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)