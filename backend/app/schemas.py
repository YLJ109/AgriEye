"""Pydantic 请求/响应模型。"""
from datetime import datetime
from pydantic import BaseModel, Field


# ---------- 识别 ----------
class RecognizeResponse(BaseModel):
    diagnosis_id: int
    coarse_category: str = Field(..., description="四大类英文键")
    coarse_label: str = Field(..., description="四大类中文名")
    fine_class: str | None = None
    fine_label: str | None = None
    confidence: float
    severity: str = "moderate"
    detection_boxes: list[dict] = Field(default_factory=list)
    scheme: dict = Field(default_factory=dict)
    rag_advice: str | None = None
    image_url: str
    created_at: datetime
    mode: str = Field("model", description="识别方式：model=真实ONNX模型, heuristic=启发式回退, unknown=未识别")


# ---------- RAG 问答 ----------
class RagQuery(BaseModel):
    question: str
    crop: str | None = None
    top_k: int = 5


class RagAnswer(BaseModel):
    answer: str
    sources: list[dict] = Field(default_factory=list)
    related_schemes: list[dict] = Field(default_factory=list)


# ---------- 治理方案 ----------
class SchemeRequest(BaseModel):
    coarse_category: str
    fine_class: str | None = None
    crop: str | None = None
    severity: str = "moderate"


class Scheme(BaseModel):
    diagnosis: str
    cause: str
    chemicals: list[dict] = Field(default_factory=list)
    green_alternatives: list[dict] = Field(default_factory=list)
    fertilization: list[dict] = Field(default_factory=list)
    prevention: list[str] = Field(default_factory=list)
    remark: str = ""


# ---------- 历史 ----------
class DiagnosisItem(BaseModel):
    id: int
    image_url: str
    coarse_label: str
    fine_label: str | None
    confidence: float
    severity: str
    created_at: datetime


class HistoryPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[DiagnosisItem]


# ---------- 农事 ----------
class ReminderCreate(BaseModel):
    crop: str | None = None
    solar_term: str | None = None
    title: str
    content: str
    priority: int = 1


class ReminderOut(BaseModel):
    id: int
    solar_term: str | None
    crop: str | None
    title: str
    content: str
    priority: int
    done: bool
    remind_date: datetime | None


# ---------- 地块 ----------
class PlotCreate(BaseModel):
    name: str
    crop: str
    area_mu: float = 0.0
    location: str | None = None
    growth_stage: str | None = None
    note: str | None = None


class PlotOut(BaseModel):
    id: int
    name: str
    crop: str
    area_mu: float
    location: str | None
    growth_stage: str | None
    note: str | None


# ---------- 认证（SEC-002）----------
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class RegisterRequest(LoginRequest):
    nickname: str | None = None
    region: str | None = None


class UserOut(BaseModel):
    id: int
    username: str | None
    nickname: str
    role: str
    region: str | None = None
    avatar: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # 有效秒数
    user: UserOut