"""历史诊断记录与地块档案路由。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_

from app.config import settings
from app.constants import FINE_LABELS_ZH
from app.core.auth import CurrentUser
from app.db.database import get_session
from app.db.models import Diagnosis, Plot, User
from app.schemas import HistoryPage, DiagnosisItem, PlotCreate, PlotOut

router = APIRouter()


@router.get("/list", response_model=HistoryPage)
async def list_history(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    coarse: str | None = Query(None, description="按大类筛选"),
    search: str | None = Query(None, description="关键词：匹配病害中文名/作物/大类（FUNC-001 下沉后端）"),
    session: AsyncSession = Depends(get_session),
):
    base = select(Diagnosis).where(Diagnosis.user_id == current_user.id)
    if coarse:
        base = base.where(Diagnosis.coarse_category == coarse)

    # 关键词搜索：中文标签 -> 英文明细类/大类，再叠加原文模糊匹配
    if search and search.strip():
        kw = search.strip()
        matched_fine = [k for k, v in FINE_LABELS_ZH.items() if kw in v]
        matched_coarse = [k for k, v in settings.coarse_labels_zh.items() if kw in v]
        conds = [Diagnosis.fine_class.ilike(f"%{kw}%")]
        if matched_fine:
            conds.append(Diagnosis.fine_class.in_(matched_fine))
        if matched_coarse:
            conds.append(Diagnosis.coarse_category.in_(matched_coarse))
        base = base.where(or_(*conds))
    total_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(total_q)).scalar_one()

    rows = (await session.execute(
        base.order_by(desc(Diagnosis.created_at))
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    items = [DiagnosisItem(
        id=r.id,
        image_url=f"/uploads/{r.image_path}",
        coarse_label=settings.coarse_labels_zh.get(r.coarse_category, r.coarse_category),
        fine_label=FINE_LABELS_ZH.get(r.fine_class or "", r.fine_class) or settings.coarse_labels_zh.get(r.coarse_category, r.coarse_category),
        confidence=round(r.confidence, 4),
        severity=r.severity,
        created_at=r.created_at,
    ) for r in rows]
    return HistoryPage(total=total, page=page, page_size=page_size, items=items)


@router.get("/detail/{diagnosis_id}")
async def detail(diagnosis_id: int, current_user: CurrentUser,
                 session: AsyncSession = Depends(get_session)):
    d = await session.get(Diagnosis, diagnosis_id)
    if not d or d.user_id != current_user.id:   # SEC-003：查别人的记录一律按不存在处理
        raise HTTPException(404, "记录不存在")
    return {
        "id": d.id, "image_url": f"/uploads/{d.image_path}",
        "coarse_category": d.coarse_category,
        "coarse_label": settings.coarse_labels_zh.get(d.coarse_category, d.coarse_category),
        "fine_class": d.fine_class,
        "fine_label": FINE_LABELS_ZH.get(d.fine_class or "", d.fine_class) or settings.coarse_labels_zh.get(d.coarse_category, d.coarse_category),
        "confidence": round(d.confidence, 4),
        "severity": d.severity,
        "detection_boxes": d.detection_boxes or [],
        "scheme": d.scheme or {},
        "rag_advice": d.rag_advice,
        "created_at": d.created_at.isoformat(),
    }


@router.delete("/{diagnosis_id}")
async def delete_diagnosis(diagnosis_id: int, current_user: CurrentUser,
                           session: AsyncSession = Depends(get_session)):
    d = await session.get(Diagnosis, diagnosis_id)
    if not d or d.user_id != current_user.id:   # SEC-003：只能删自己的
        raise HTTPException(404, "记录不存在")
    await session.delete(d)
    await session.commit()
    return {"ok": True}


# ---------- 地块档案 ----------
@router.get("/plots", response_model=list[PlotOut])
async def list_plots(current_user: CurrentUser, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(Plot).where(Plot.user_id == current_user.id).order_by(desc(Plot.created_at))
    )).scalars().all()
    return [PlotOut(id=r.id, name=r.name, crop=r.crop, area_mu=r.area_mu,
                    location=r.location, growth_stage=r.growth_stage, note=r.note) for r in rows]


@router.post("/plots", response_model=PlotOut)
async def create_plot(payload: PlotCreate, current_user: CurrentUser,
                      session: AsyncSession = Depends(get_session)):
    plot = Plot(user_id=current_user.id, **payload.model_dump())
    session.add(plot)
    await session.commit()
    await session.refresh(plot)
    return PlotOut(id=plot.id, name=plot.name, crop=plot.crop, area_mu=plot.area_mu,
                   location=plot.location, growth_stage=plot.growth_stage, note=plot.note)