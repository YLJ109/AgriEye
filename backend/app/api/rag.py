"""RAG 农事问答路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.core.rag_engine import rag_engine
from app.core.scheme_generator import generate_scheme
from app.schemas import RagQuery, RagAnswer

router = APIRouter()


@router.post("/ask", response_model=RagAnswer)
async def ask(query: RagQuery):
    """AI 农事顾问问答。"""
    res = rag_engine.answer(query.question, crop=query.crop, top_k=query.top_k)
    # 若问题涉及治理，附带相关方案
    related = []
    for kw, coarse in [("病", "fungal_disease"), ("虫", "pest"),
                       ("缺肥", "deficiency"), ("黄化", "deficiency"),
                       ("药害", "phytotoxicity")]:
        if kw in query.question:
            scheme = generate_scheme(coarse, crop=query.crop)
            related.append({"category": coarse, "scheme": scheme})
            break
    return RagAnswer(
        answer=res.get("answer", ""),
        sources=res.get("sources", []),
        related_schemes=related,
    )


@router.get("/search")
async def search(q: str, top_k: int = 5):
    """纯检索接口（用于前端联想/知识浏览）。"""
    hits = rag_engine.retrieve(q, top_k=top_k)
    return {"query": q, "results": [
        {"text": h.text, "source": h.source, "score": round(h.score, 3),
         "metadata": h.metadata} for h in hits
    ]}