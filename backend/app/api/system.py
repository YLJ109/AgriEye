"""系统状态路由 - 健康检查、模型状态、统计概览。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import settings
from app.core.auth import CurrentUser
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
async def stats(current_user: CurrentUser, session: AsyncSession = Depends(get_session)):
    """统计口径固定为「当前登录用户自己的数据」（SEC-003）。"""
    total = (await session.execute(
        select(func.count()).where(Diagnosis.user_id == current_user.id)
    )).scalar_one()
    # 按大类统计
    rows = (await session.execute(
        select(Diagnosis.coarse_category, func.count())
        .where(Diagnosis.user_id == current_user.id)
        .group_by(Diagnosis.coarse_category)
    )).all()
    # FUNC-006：统计口径统一用英文 key（稳定、不受文案改动影响），
    # 中文标签另给一张映射表，展示层按需取用。
    by_category = {k: v for k, v in rows}
    by_category_labels = {k: settings.coarse_labels_zh.get(k, k) for k, _ in rows}
    return {
        "total_diagnoses": total,
        "by_category": by_category,
        "by_category_labels": by_category_labels,
        "categories_supported": len(settings.coarse_categories),
        "fine_classes_supported": len(settings.fine_classes),
    }