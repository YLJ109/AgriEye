"""RAG 向量知识库构建脚本。

将 knowledge/*.json 转为向量索引（FAISS），供后端 RAG 引擎检索。
独立运行：python backend/knowledge/build_vector_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# 允许独立运行：把 backend 加入 path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings  # noqa: E402
from app.core.rag_engine import rag_engine  # noqa: E402
from loguru import logger  # noqa: E402


def build_vector_db() -> None:
    """构建并持久化向量索引。"""
    logger.info(f"知识库目录：{settings.knowledge_dir}")
    files = list(settings.knowledge_dir.glob("*.json"))
    logger.info(f"发现知识文件：{[f.name for f in files]}")

    # 强制重新构建
    rag_engine._loaded = False
    rag_engine._index = None
    rag_engine._chunks = []
    rag_engine.load()

    if not rag_engine._chunks:
        logger.error("未加载到任何知识片段，请检查 knowledge/*.json")
        return

    logger.info(f"知识片段总数：{len(rag_engine._chunks)}")
    if rag_engine._index is not None:
        logger.info(f"FAISS 索引已保存至：{settings.vector_db_path / 'agri.index'}")
    else:
        logger.info("使用关键词检索模式（无嵌入模型）")

    # 抽样验证检索
    for q in ["水稻稻瘟病怎么治", "小麦缺氮黄化怎么办", "玉米螟防治", "农药药害怎么处理"]:
        hits = rag_engine.retrieve(q, top_k=2)
        logger.info(f"验证检索「{q}」-> 命中 {len(hits)} 条")
        for h in hits[:1]:
            logger.info(f"  top1: [{h.source}] {h.text[:60]}...")


if __name__ == "__main__":
    build_vector_db()