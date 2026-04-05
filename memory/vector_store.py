"""
memory/vector_store.py
ChromaDB向量记忆层：存储章节摘要和关键叙事片段，支持语义检索
"""

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class VectorStore:
    """
    每个项目一个ChromaDB Collection。
    存储内容：章节摘要 + 关键片段（角色情感变化、伏笔节点等）
    """

    def __init__(self, vector_path: str, embedding_model: str):
        """
        vector_path: 向量库持久化目录（每个项目独立）
        embedding_model: HuggingFace模型名，如 'shibing624/text2vec-base-chinese'
        """
        Path(vector_path).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=vector_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._model = None
        self._embedding_model_name = embedding_model

        # 获取或创建collection（禁用ChromaDB内置embedding，自己做）
        self.collection = self.client.get_or_create_collection(
            name="story_memory",
            metadata={"hnsw:space": "cosine"},
        )

    def _get_model(self) -> SentenceTransformer:
        """懒加载embedding模型"""
        if self._model is None:
            self._model = SentenceTransformer(self._embedding_model_name)
        return self._model

    def _embed(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    # ------------------------------------------------------------------
    # 写入接口
    # ------------------------------------------------------------------

    def add_chapter_summary(
        self,
        chapter_number: int,
        summary: str,
        title: str = "",
        metadata: Optional[dict] = None,
    ) -> None:
        """存储章节摘要"""
        doc_id = f"chapter_{chapter_number}_summary"
        meta = {
            "type": "chapter_summary",
            "chapter_number": chapter_number,
            "title": title,
        }
        if metadata:
            meta.update(metadata)

        embeddings = self._embed([summary])
        self.collection.upsert(
            ids=[doc_id],
            embeddings=embeddings,
            documents=[summary],
            metadatas=[meta],
        )

    def add_story_fragment(
        self,
        fragment_id: str,
        text: str,
        fragment_type: str,
        chapter_number: int,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        存储关键叙事片段（角色情感爆发、伏笔埋设处等）
        fragment_type: 'character_moment' | 'foreshadowing' | 'worldbuilding' | 'key_scene'
        """
        meta = {
            "type": fragment_type,
            "chapter_number": chapter_number,
        }
        if metadata:
            meta.update(metadata)

        embeddings = self._embed([text])
        self.collection.upsert(
            ids=[fragment_id],
            embeddings=embeddings,
            documents=[text],
            metadatas=[meta],
        )

    # ------------------------------------------------------------------
    # 检索接口
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_type: Optional[str] = None,
    ) -> list[dict]:
        """
        语义搜索。
        返回 list of { text, metadata, distance }
        """
        if self.collection.count() == 0:
            return []

        query_embedding = self._embed([query])
        where = {"type": filter_type} if filter_type else None

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, self.collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({"text": doc, "metadata": meta, "distance": dist})
        return output

    def search_chapter_summaries(self, query: str, n_results: int = 3) -> list[dict]:
        return self.search(query, n_results=n_results, filter_type="chapter_summary")

    def search_story_fragments(self, query: str, n_results: int = 5) -> list[dict]:
        """搜索非摘要类片段（角色时刻、世界观等）"""
        if self.collection.count() == 0:
            return []
        query_embedding = self._embed([query])
        where = {"type": {"$ne": "chapter_summary"}}
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, self.collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({"text": doc, "metadata": meta, "distance": dist})
        return output

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def format_search_results(self, results: list[dict]) -> str:
        """将检索结果格式化为可插入prompt的文本"""
        if not results:
            return "（无相关历史内容）"
        lines = []
        for r in results:
            meta = r["metadata"]
            ch = meta.get("chapter_number", "?")
            t = meta.get("type", "fragment")
            lines.append(f"[第{ch}章 {t}] {r['text']}")
        return "\n---\n".join(lines)
