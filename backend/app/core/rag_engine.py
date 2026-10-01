"""农业垂直 RAG 知识库引擎。

流程：知识文档切片 -> 多语言句向量嵌入 -> FAISS 向量索引 -> 检索 Top-K -> 拼接上下文。
离线优先：嵌入模型本地缓存，FAISS 纯 CPU，无任何外部 API 依赖。
"""
from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

import numpy as np
from loguru import logger

from app.config import settings


@dataclass
class RagHit:
    text: str
    score: float
    source: str
    metadata: dict


class RagEngine:
    def __init__(self) -> None:
        self._embedder = None
        self._index = None  # faiss index
        self._chunks: list[dict] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._load_embedder()
        self._build_or_load_index()
        self._loaded = True
        logger.info(f"RAG 引擎就绪，知识片段数：{len(self._chunks)}")

    # ---------- 嵌入模型 ----------
    def _load_embedder(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(
                settings.embedding_model, device=settings.device
            )
            logger.info("句向量嵌入模型加载完成")
        except Exception as e:
            logger.warning(f"嵌入模型加载失败，使用 TF-IDF 关键词回退：{e}")
            self._embedder = None

    # ---------- 索引构建 ----------
    def _build_or_load_index(self) -> None:
        chunks = self._load_knowledge_chunks()
        self._chunks = chunks
        if not chunks:
            logger.warning("知识库为空，请先运行 knowledge/build_vector_db.py")
            return
        if self._embedder is not None:
            self._build_faiss(chunks)

    def _load_knowledge_chunks(self) -> list[dict]:
        """从 knowledge/*.json 加载并切片。"""
        chunks: list[dict] = []
        for fp in sorted(settings.knowledge_dir.glob("*.json")):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"读取知识文件失败 {fp.name}: {e}")
                continue
            source = fp.stem
            if isinstance(data, list):
                for item in data:
                    chunks.append(self._chunk_item(item, source))
            elif isinstance(data, dict):
                for key, val in data.items():
                    if isinstance(val, list):
                        for item in val:
                            chunks.append(self._chunk_item(item, source, section=key))
                    else:
                        chunks.append(self._chunk_item({"content": str(val)}, source, section=key))
        return [c for c in chunks if c.get("text")]

    @staticmethod
    def _chunk_item(item: dict, source: str, section: str = "") -> dict:
        text = item.get("content") or item.get("text") or item.get("advice") or ""
        if not text and item:
            text = "；".join(f"{k}：{v}" for k, v in item.items() if v)
        return {
            "text": str(text),
            "source": source,
            "section": section,
            "metadata": {k: v for k, v in item.items() if k not in ("content", "text", "advice")},
        }

    def _build_faiss(self, chunks: list[dict]) -> None:
        import faiss
        texts = [c["text"] for c in chunks]
        vecs = self._embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        vecs = np.asarray(vecs, dtype=np.float32)
        dim = vecs.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(vecs)
        faiss.write_index(self._index, str(settings.vector_db_path / "agri.index"))
        logger.info(f"FAISS 索引构建完成，维度 {dim}，片段 {len(chunks)}")

    # ---------- 检索 ----------
    def retrieve(self, query: str, top_k: int = 5) -> list[RagHit]:
        self.load()
        if not self._chunks:
            return []
        if self._index is not None and self._embedder is not None:
            return self._retrieve_faiss(query, top_k)
        return self._retrieve_keyword(query, top_k)

    def _retrieve_faiss(self, query: str, top_k: int) -> list[RagHit]:
        qv = self._embedder.encode([query], normalize_embeddings=True)
        qv = np.asarray(qv, dtype=np.float32)
        k = min(top_k, len(self._chunks))
        scores, idxs = self._index.search(qv, k)
        hits = []
        for sc, idx in zip(scores[0], idxs[0]):
            if idx < 0 or sc < settings.rag_score_threshold:
                continue
            c = self._chunks[idx]
            hits.append(RagHit(c["text"], float(sc), c["source"], c["metadata"]))
        return hits

    def _retrieve_keyword(self, query: str, top_k: int) -> list[RagHit]:
        """无嵌入模型时的关键词召回回退。"""
        import jieba
        q_tokens = set(jieba.cut(query))
        scored = []
        for c in self._chunks:
            tokens = set(jieba.cut(c["text"]))
            overlap = len(q_tokens & tokens)
            if overlap > 0:
                scored.append((overlap / (len(q_tokens) + 1e-6), c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [RagHit(c["text"], s, c["source"], c["metadata"]) for s, c in scored[:top_k]]

    # ---------- 生成回答 ----------
    def answer(self, question: str, crop: str | None = None, top_k: int = 5) -> dict:
        q = f"{crop} {question}" if crop else question
        hits = self.retrieve(q, top_k)
        if not hits:
            return {"answer": "暂未检索到相关农业知识，建议咨询当地农技专家。", "sources": []}
        context = "\n\n".join(f"【知识{i+1}】{h.text}" for i, h in enumerate(hits))
        answer = self._compose_answer(question, crop, hits, context)
        sources = [{"source": h.source, "score": round(h.score, 3),
                    "snippet": h.text[:80]} for h in hits]
        return {"answer": answer, "sources": sources, "context": context}

    @staticmethod
    def _compose_answer(question: str, crop: str | None, hits: list[RagHit], context: str) -> str:
        """离线模板化生成（无大模型 API 依赖），整合检索片段。"""
        crop_str = f"【{crop}】" if crop else ""
        lines = [f"针对您的问题「{question}」，结合农业知识库给出如下建议："]
        for i, h in enumerate(hits, 1):
            lines.append(f"\n{i}. {h.text}")
        lines.append("\n—— 以上内容来自本地农业垂直知识库 RAG 检索，可结合当地实际调整。")
        return crop_str + "\n".join(lines)


rag_engine = RagEngine()