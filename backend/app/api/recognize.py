"""图像识别路由 - 上传图片 -> 推理 -> 生成方案 -> 落库 -> 返回。"""
import asyncio
import time
from pathlib import Path

import cv2
import numpy as np
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.config import settings
from app.constants import FINE_LABELS_ZH, SCHEMA_VERSION
from app.core.auth import CurrentUser
from app.db.database import get_session
from app.db.models import User, Diagnosis
from app.core.model_inference import inference_engine
from app.core.scheme_generator import generate_scheme
from app.schemas import RecognizeResponse

router = APIRouter()


def _sniff_image_magic(raw: bytes) -> bool:
    """按文件头魔数判断真实图片类型（SEC-007）。

    扩展名由客户端提供、可任意伪造（把 .exe 改名 .jpg 也能通过扩展名校验），
    因此以字节签名为准。只放行白名单里与 allowed_extensions 对应的格式。
    """
    if len(raw) < 12:
        return False
    if raw[:8] == b"\x89PNG\r\n\x1a\n":                       # PNG
        return True
    if raw[:3] == b"\xff\xd8\xff":                            # JPEG
        return True
    if raw[:2] == b"BM":                                      # BMP
        return True
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":           # WEBP
        return True
    return False


@router.post("", response_model=RecognizeResponse)
async def recognize(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    plot_id: int | None = Form(None),
    crop: str | None = Form(None),
    preview: bool = Form(False),
    session: AsyncSession = Depends(get_session),
):
    # ---------- 校验 ----------
    original_name = file.filename or "upload.jpg"
    ext = Path(original_name).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(400, f"不支持的图片格式，允许：{settings.allowed_extensions}")
    raw = await file.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"图片过大，限制 {settings.max_upload_mb}MB")
    if not raw:
        raise HTTPException(400, "图片内容为空")
    # SEC-007：扩展名可伪造，按文件头魔数再验一次真实类型
    if not _sniff_image_magic(raw):
        raise HTTPException(400, "文件内容不是有效图片（扩展名与真实格式不符）")

    # ---------- 保存 ----------
    safe_name = Path(original_name).name.replace("/", "_").replace("\\", "_")
    save_name = f"{inference_engine.image_hash(np.frombuffer(raw[:64], dtype=np.uint8))}_{safe_name}"
    save_path = settings.upload_dir / save_name
    save_path.write_bytes(raw)

    # ---------- 推理 ----------
    img_array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400, "图片解码失败")
    # EXIF 旋转校正（处理手机拍照方向）
    try:
        from PIL import Image
        import io
        pil_img = Image.open(io.BytesIO(raw))
        orientation = pil_img.getexif().get(274, 1)
        if orientation in (3, 6, 8):
            image = cv2.rotate(image, {
                3: cv2.ROTATE_180,
                6: cv2.ROTATE_90_CLOCKWISE,
                8: cv2.ROTATE_90_COUNTERCLOCKWISE,
            }[orientation])
    except Exception:
        pass
    # 异步推理（避免阻塞事件循环）并记录耗时
    t0 = time.time()
    result = await asyncio.get_event_loop().run_in_executor(None, inference_engine.predict, image)
    logger.info(f"识别结果：{result.coarse_category}/{result.fine_class} conf={result.confidence:.3f} 耗时={time.time()-t0:.3f}s")

    # ---------- 生成方案 ----------
    scheme = generate_scheme(
        coarse_category=result.coarse_category,
        fine_class=result.fine_class,
        crop=crop,
        severity=result.severity,
    )
    scheme["schema_version"] = SCHEMA_VERSION   # DATA-004

    # ---------- 落库 ----------
    # 默认占位：保证 preview 路径与异常路径下 diagnosis_id/created_at 始终有值，
    # 避免 UnboundLocalError（局部变量仅在分支内赋值却在分支外被读取）。
    diagnosis_id = 0
    # DATA-001：与 ORM 的 default=datetime.utcnow 保持一致，全链路统一 UTC 入库
    created_at = datetime.utcnow()
    if not preview:
        diag = Diagnosis(
            user_id=current_user.id,
            plot_id=plot_id,
            image_path=save_name,
            coarse_category=result.coarse_category,
            fine_class=result.fine_class,
            confidence=result.confidence,
            severity=result.severity,
            detection_boxes=result.boxes,
            scheme=scheme,
            rag_advice=scheme.get("rag_advice"),
        )
        session.add(diag)
        await session.commit()
        await session.refresh(diag)
        diagnosis_id = diag.id
        created_at = diag.created_at

    return RecognizeResponse(
        diagnosis_id=diagnosis_id,
        coarse_category=result.coarse_category,
        coarse_label=settings.coarse_labels_zh.get(result.coarse_category, result.coarse_category),
        fine_class=result.fine_class,
        fine_label=FINE_LABELS_ZH.get(result.fine_class or "", "")
                  or ("未识别" if result.mode == "unknown" else "—"),
        confidence=round(result.confidence, 4),
        severity=result.severity,
        detection_boxes=result.boxes,
        scheme=scheme,
        rag_advice=scheme.get("rag_advice"),
        image_url=f"/uploads/{save_name}",
        created_at=created_at,
        mode=result.mode,
    )


@router.post("/store")
async def store_diagnosis(
    current_user: CurrentUser,
    image_path: str = Form(...),
    coarse_category: str = Form(...),
    fine_class: str = Form(None),
    confidence: float = Form(0.0),
    severity: str = Form("moderate"),
    detection_boxes: str = Form("[]"),
    scheme: str = Form("{}"),
    rag_advice: str = Form(None),
    session: AsyncSession = Depends(get_session),
):
    """审核通过后存储诊断记录。"""
    import json
    # 前端传来的 JSON 字符串可能为空或格式异常，逐项容错，避免整条记录写不进去（FUNC-003）
    try:
        boxes = json.loads(detection_boxes) if detection_boxes else []
        if not isinstance(boxes, list):
            boxes = []
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"detection_boxes 解析失败，按空列表处理：{detection_boxes!r}")
        boxes = []
    try:
        scheme_obj = json.loads(scheme) if scheme else {}
        if not isinstance(scheme_obj, dict):
            scheme_obj = {}
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"scheme 解析失败，按空字典处理：{scheme!r}")
        scheme_obj = {}
    scheme_obj.setdefault("schema_version", SCHEMA_VERSION)   # DATA-004：结构版本，便于后续兼容升级

    # CONC-001：同一用户对同一张图重复提交（网络重试/误点）不再产生重复记录
    if image_path:
        dup = (await session.execute(
            select(Diagnosis).where(
                Diagnosis.user_id == current_user.id,
                Diagnosis.image_path == image_path,
            )
        )).scalars().first()
        if dup:
            logger.info(f"重复的入库请求，返回已有记录 id={dup.id}")
            return {"ok": True, "id": dup.id, "duplicated": True}

    diag = Diagnosis(
        user_id=current_user.id,
        image_path=image_path,
        coarse_category=coarse_category,
        fine_class=fine_class,
        confidence=confidence,
        severity=severity,
        detection_boxes=boxes,
        scheme=scheme_obj,
        rag_advice=rag_advice,
    )
    session.add(diag)
    await session.commit()
    await session.refresh(diag)
    return {"diagnosis_id": diag.id, "ok": True}


@router.get("/{diagnosis_id}", response_model=RecognizeResponse)
async def get_diagnosis(diagnosis_id: int, session: AsyncSession = Depends(get_session)):
    d = await session.get(Diagnosis, diagnosis_id)
    if not d:
        raise HTTPException(404, "诊断记录不存在")
    return RecognizeResponse(
        diagnosis_id=d.id,
        coarse_category=d.coarse_category,
        coarse_label=settings.coarse_labels_zh.get(d.coarse_category, d.coarse_category),
        fine_class=d.fine_class,
        fine_label=FINE_LABELS_ZH.get(d.fine_class or "", d.fine_class) or settings.coarse_labels_zh.get(d.coarse_category, d.coarse_category),
        confidence=d.confidence,
        severity=d.severity,
        detection_boxes=d.detection_boxes or [],
        scheme=d.scheme or {},
        rag_advice=d.rag_advice,
        image_url=f"/uploads/{d.image_path}",
        created_at=d.created_at,
    )