"""系统状态路由 - 健康检查、模型状态、统计概览。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import settings
from app.db.database import get_session
from app.db.models import Diagnosis, User

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "version": "1.0.0"}


@router.get("/info")
async def info():
    return {
        "app_name": settings.app_name,
        "categories": settings.coarse_labels_zh,
        "fine_classes_count": len(settings.fine_classes),
        "device": settings.device,
        "offline_ready": True,
        "model_loaded": settings.model_path.exists(),
    }


@router.get("/stats")
async def stats(user_id: int = 1, session: AsyncSession = Depends(get_session)):
    total = (await session.execute(
        select(func.count()).where(Diagnosis.user_id == user_id)
    )).scalar_one()
    # 按大类统计
    rows = (await session.execute(
        select(Diagnosis.coarse_category, func.count())
        .where(Diagnosis.user_id == user_id)
        .group_by(Diagnosis.coarse_category)
    )).all()
    by_category = {settings.coarse_labels_zh.get(k, k): v for k, v in rows}
    return {
        "total_diagnoses": total,
        "by_category": by_category,
        "categories_supported": len(settings.coarse_categories),
        "fine_classes_supported": len(settings.fine_classes),
    }