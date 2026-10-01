"""图像识别路由 - 上传图片 -> 推理 -> 生成方案 -> 落库 -> 返回。"""
import asyncio
import json
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
from app.schemas import RecognizeResponse, as_utc

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


def _parse_json_field(raw: str | None, field: str, expect: type, default):
    """校验 multipart 里以字符串传递的 JSON 字段（FUNC-003）。

    - 空/未传 -> 用默认值（合法场景：前端确实没有检测框或方案）
    - 有值但非法 JSON 或类型不符 -> 422，附字段名与原因，便于调用方定位
    """
    if raw is None or raw.strip() == "":
        return default if isinstance(default, expect) else default
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(422, f"参数格式错误：{field} 不是合法 JSON（{e}）")
    if not isinstance(value, expect):
        raise HTTPException(422, f"参数格式错误：{field} 应为 {expect.__name__}，实际为 {type(value).__name__}")
    return value


def _promote_preview_file(image_path: str | None) -> str | None:
    """把预览临时目录里的文件搬进正式 uploads（DATA-003）。

    前端可能传 /preview_tmp/xxx.jpg 也可能直接传 xxx.jpg，两种都兼容；
    目标文件已存在时视为同一张图（内容哈希命名），直接复用不重复搬运。
    """
    if not image_path:
        return image_path
    name = image_path.replace("/preview_tmp/", "").replace("/uploads/", "").lstrip("/")
    if not name:
        return image_path
    src = settings.preview_tmp_dir / name
    dst = settings.upload_dir / name
    if src.exists() and not dst.exists():
        try:
            import shutil
            shutil.move(str(src), str(dst))
            logger.info(f"预览文件已转入正式目录：{name}")
        except OSError as e:
            logger.warning(f"预览文件搬移失败，沿用原路径：{name} - {e}")
            return name
    return name


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
    save_name = f"{inference_engine.image_hash(raw)}_{safe_name}"
    # DATA-003：预览检测写临时目录，不再污染正式 uploads（连续预览不会产生文件堆积）；
    # 审核通过时由 /store 搬到 upload_dir。
    target_dir = settings.preview_tmp_dir if preview else settings.upload_dir
    save_path = target_dir / save_name
    try:
        save_path.write_bytes(raw)
    except OSError as e:
        logger.error(f"保存上传文件失败：{save_path} - {e}")
        raise HTTPException(500, "图片保存失败")
    image_url_prefix = "/preview_tmp" if preview else "/uploads"

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
        image_url=f"{image_url_prefix}/{save_name}",
        created_at=as_utc(created_at),
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
    # FUNC-003：两个 JSON 字段按验收口径严格校验 —— 空值视为「未提供」用默认值，
    # 有值但解析失败或类型不符直接 422，不再静默吞掉（此前是容错写空，与验收不一致）。
    boxes = _parse_json_field(detection_boxes, "detection_boxes", list, [])
    scheme_obj = _parse_json_field(scheme, "scheme", dict, {})
    scheme_obj.setdefault("schema_version", SCHEMA_VERSION)   # DATA-004：结构版本，便于后续兼容升级

    # DATA-003：预览阶段的文件还在临时目录，审核通过时搬到正式 uploads，
    # 并把 image_path 改写为最终落点，保证 /uploads/{path} 可被访问。
    image_path = _promote_preview_file(image_path)

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