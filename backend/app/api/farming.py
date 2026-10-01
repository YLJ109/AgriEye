"""农事提醒与节气种植建议路由。"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.database import get_session
from app.db.models import FarmingReminder
from app.schemas import ReminderCreate, ReminderOut

router = APIRouter()

# 二十四节气与农事要点（北方/通用简化版）
SOLAR_TERMS = [
    ("立春", "春耕备耕，整地施肥，准备种子农资"),
    ("雨水", "麦田追肥，果树修剪，防倒春寒"),
    ("惊蛰", "病虫害防治关键期，清园喷石硫合剂"),
    ("春分", "播种春作物，水稻育秧，果树花前管理"),
    ("清明", "播种移栽，玉米花生下种，防地下害虫"),
    ("谷雨", "水稻插秧，蔬菜定植，雨后追肥"),
    ("立夏", "夏播准备，小麦赤霉病防治，果树疏果"),
    ("小满", "防干热风，灌浆期管理，防蚜虫"),
    ("芒种", "抢收抢种，水稻分蘖期追肥，防稻瘟病"),
    ("夏至", "防涝排涝，玉米中耕除草，防玉米螟"),
    ("小暑", "高温防虫，果树防红蜘蛛，蔬菜防日灼"),
    ("大暑", "防旱防涝，水稻抽穗期防稻飞虱"),
    ("立秋", "秋收准备，果树秋施基肥，防早期落叶病"),
    ("处暑", "晚稻追肥，蔬菜育苗，防秋老虎"),
    ("白露", "秋播准备，小麦备播，果树控水促花芽"),
    ("秋分", "小麦播种最佳期，施足底肥"),
    ("寒露", "防早霜，收获晚秋作物，冬灌准备"),
    ("霜降", "收获入库，果树清园，防冻害"),
    ("立冬", "冬灌，果树涂白防冻，清园越冬"),
    ("小雪", "防冻保暖，大棚管理，蓄肥备冬"),
    ("大雪", "大棚防寒，畜禽保暖，检修农具"),
    ("冬至", "冬闲备耕，积造有机肥，规划来年"),
    ("小寒", "防极端低温，果树防寒，大棚增温"),
    ("大寒", "备春耕，购农资，制定全年种植计划"),
]


@router.get("/solar-terms")
async def solar_terms():
    """返回二十四节气农事建议。"""
    now = datetime.now()
    return {
        "current_month": now.month,
        "terms": [{"term": t, "advice": a} for t, a in SOLAR_TERMS],
    }


@router.get("/current-advice")
async def current_advice(crop: str | None = None):
    """根据当前日期给出节气农事建议。"""
    now = datetime.now()
    # 简化：按月份映射节气
    month_term = {
        2: "立春", 3: "惊蛰", 4: "清明", 5: "立夏", 6: "芒种",
        7: "小暑", 8: "立秋", 9: "白露", 10: "寒露", 11: "立冬", 12: "冬至",
        1: "小寒",
    }
    term = month_term.get(now.month, "立春")
    advice = next((a for t, a in SOLAR_TERMS if t == term), "")
    return {
        "date": now.date().isoformat(),
        "solar_term": term,
        "advice": advice,
        "crop_tip": f"【{crop}】当前阶段注意水肥管理与病虫害预防。" if crop else "",
    }


@router.get("/reminders", response_model=list[ReminderOut])
async def list_reminders(user_id: int = Query(1), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(FarmingReminder).where(
            (FarmingReminder.user_id == user_id) | (FarmingReminder.user_id.is_(None))
        ).order_by(desc(FarmingReminder.created_at))
    )).scalars().all()
    return [_to_out(r) for r in rows]


@router.post("/reminders", response_model=ReminderOut)
async def create_reminder(payload: ReminderCreate, user_id: int = Query(1),
                           session: AsyncSession = Depends(get_session)):
    r = FarmingReminder(user_id=user_id, **payload.model_dump())
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return _to_out(r)


@router.patch("/reminders/{rid}/done")
async def mark_done(rid: int, session: AsyncSession = Depends(get_session)):
    r = await session.get(FarmingReminder, rid)
    if not r:
        raise HTTPException(404, "提醒不存在")
    r.done = not r.done
    await session.commit()
    return {"ok": True, "done": r.done}


@router.delete("/reminders/{rid}")
async def delete_reminder(rid: int, session: AsyncSession = Depends(get_session)):
    r = await session.get(FarmingReminder, rid)
    if not r:
        raise HTTPException(404, "提醒不存在")
    await session.delete(r)
    await session.commit()
    return {"ok": True}


def _to_out(r: FarmingReminder) -> ReminderOut:
    return ReminderOut(id=r.id, solar_term=r.solar_term, crop=r.crop, title=r.title,
                       content=r.content, priority=r.priority, done=r.done,
                       remind_date=r.remind_date)