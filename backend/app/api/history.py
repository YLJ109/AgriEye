"""历史诊断记录与地块档案路由。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.config import settings
from app.constants import FINE_LABELS_ZH
from app.db.database import get_session
from app.db.models import Diagnosis, Plot, User
from app.schemas import HistoryPage, DiagnosisItem, PlotCreate, PlotOut

router = APIRouter()


@router.get("/list", response_model=HistoryPage)
async def list_history(
    user_id: int = Query(1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    coarse: str | None = Query(None, description="按大类筛选"),
    session: AsyncSession = Depends(get_session),
):
    base = select(Diagnosis).where(Diagnosis.user_id == user_id)
    if coarse:
        base = base.where(Diagnosis.coarse_category == coarse)
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
async def detail(diagnosis_id: int, session: AsyncSession = Depends(get_session)):
    d = await session.get(Diagnosis, diagnosis_id)
    if not d:
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
async def delete_diagnosis(diagnosis_id: int, session: AsyncSession = Depends(get_session)):
    d = await session.get(Diagnosis, diagnosis_id)
    if not d:
        raise HTTPException(404, "记录不存在")
    await session.delete(d)
    await session.commit()
    return {"ok": True}


# ---------- 地块档案 ----------
@router.get("/plots", response_model=list[PlotOut])
async def list_plots(user_id: int = Query(1), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(Plot).where(Plot.user_id == user_id).order_by(desc(Plot.created_at))
    )).scalars().all()
    return [PlotOut(id=r.id, name=r.name, crop=r.crop, area_mu=r.area_mu,
                    location=r.location, growth_stage=r.growth_stage, note=r.note) for r in rows]


@router.post("/plots", response_model=PlotOut)
async def create_plot(payload: PlotCreate, user_id: int = Query(1), session: AsyncSession = Depends(get_session)):
    plot = Plot(user_id=user_id, **payload.model_dump())
    session.add(plot)
    await session.commit()
    await session.refresh(plot)
    return PlotOut(id=plot.id, name=plot.name, crop=plot.crop, area_mu=plot.area_mu,
                   location=plot.location, growth_stage=plot.growth_stage, note=plot.note)