"""
orchestrator/pipeline.py
Pipeline：叙事解构 → 导演审查 → 导演规划 → 编剧 → 作家 → 摘要 → 存储
"""

import json
import re
from pathlib import Path
from typing import Callable, Optional

from agents.director import DirectorAgent
from agents.screenwriter import ScreenwriterAgent
from agents.writer import WriterAgent
from inference.deepseek_client import DeepSeekInference
from memory.context_builder import ContextBuilder
from memory.store import StoryDatabase
from memory.vector_store import VectorStore


class ChapterPipeline:
    """单章生成 Pipeline（里程碑式导演架构 + 编剧 + 作家）"""

    def __init__(self, project_id: str, config: dict):
        self.project_id = project_id
        self.config = config

        self.inference = DeepSeekInference(config)
        self.db = StoryDatabase(config, project_id=project_id)
        self.director = DirectorAgent(self.inference)
        self.screenwriter = ScreenwriterAgent(self.inference)
        self.writer = WriterAgent(self.inference)

        # 向量存储
        vector_path = config["memory"]["vector_path"].format(project_id=project_id)
        embedding_model = config["memory"]["embedding_model"]
        self.vector_store = VectorStore(vector_path, embedding_model)

        self.context_builder = ContextBuilder(self.db, self.vector_store, config)

    def generate_chapter(
        self,
        on_token: Optional[Callable[[str], None]] = None,
        on_paragraph_ready: Optional[Callable[[str], None]] = None,
        on_stage: Optional[Callable[[str, str], None]] = None,
    ) -> dict:
        """
        生成下一章完整内容。

        on_token:         每收到一个写作 token 时调用
        on_paragraph_ready: 章节完成后调用一次，传入完整正文
        on_stage:         阶段切换回调 (stage_key, message)
        """

        def _stage(key: str, msg: str) -> None:
            print(msg, flush=True)
            if on_stage:
                on_stage(key, msg)

        chapter_num = self.db.get_chapter_count(self.project_id) + 1

        # ============================================================
        # 阶段0：叙事解构（首章或到达里程碑时生成）
        # ============================================================
        if self.director.should_regenerate_architecture(self.project_id, self.db):
            if chapter_num == 1:
                _stage("architecture", "\n[导演] 正在生成全篇叙事解构...")
            else:
                _stage("architecture", f"\n[导演] 到达里程碑，生成新一段叙事解构...")

            arch = self.director.create_narrative_architecture(
                self.project_id, self.db, on_stage=on_stage
            )
            if "error" in arch:
                raise RuntimeError(
                    f"【核心熔断】叙事解构生成失败: {arch.get('error')}\n"
                    f"原始输出: {arch.get('raw', '')[:500]}"
                )

        # ============================================================
        # 阶段1：导演审查上一章（首章跳过）
        # ============================================================
        if chapter_num > 1:
            _stage("review", f"[导演] 审查第 {chapter_num - 1} 章...")
            review = self.director.review_previous_chapter(
                self.project_id, self.db
            )

            score = review.get("score", "?")
            needs_revision = review.get("needs_revision", False)
            deviations = review.get("deviations", [])
            print(f"[导演] 审查评分：{score}/10，{'需要修改' if needs_revision else '通过'}")

            if deviations:
                for dev in deviations[:3]:
                    print(f"  偏差：{dev}")

            # 如需修改：调用作家重写上一章
            if needs_revision:
                revision_notes = review.get("revision_notes", "")
                _stage("rewrite", f"[作家] 根据导演意见重写第 {chapter_num - 1} 章...")
                rewritten = self._rewrite_previous_chapter(
                    chapter_num - 1, revision_notes, on_token
                )
                # 更新存储
                new_summary = self._generate_summary(rewritten)
                self.db.update_chapter_text(
                    self.project_id, chapter_num - 1, rewritten, new_summary
                )
                print(f"\n[作家] 重写完成，字数：{len(rewritten)}")

            # 如有架构调整建议
            arch_adj = review.get("architecture_adjustments", "")
            if arch_adj:
                print(f"[导演] 架构微调备注：{arch_adj[:100]}")

        # ============================================================
        # 阶段2：导演规划本章
        # ============================================================
        _stage("director", f"\n[导演] 规划第 {chapter_num} 章...")
        plan = self.director.plan_chapter(self.project_id, self.db)

        if "error" in plan or not plan.get("key_scenes"):
            err_msg = plan.get("error", "JSON解析失败或关键字段缺失")
            raw_content = plan.get("raw", "")[:500]
            raise RuntimeError(
                f"【核心熔断】导演规划阶段失败: {err_msg}\n原始输出: {raw_content}"
            )

        plan["chapter_number"] = chapter_num
        title = plan.get("chapter_title_hint", f"第{chapter_num}章")
        narrative_goal = plan.get("narrative_goal", "")
        print(f"[导演] 规划完成：第{chapter_num}章《{title}》- {narrative_goal}")

        # ============================================================
        # 阶段3：编剧细化
        # ============================================================
        _stage("screenwriter", f"[编剧] 细化第 {chapter_num} 章场景大纲...")
        outline = self.screenwriter.outline_chapter(self.project_id, self.db, plan)

        if "error" in outline:
            err_msg = outline.get("error", "编剧大纲解析失败")
            raw_content = outline.get("raw", "")[:500]
            raise RuntimeError(
                f"【核心熔断】编剧大纲阶段失败: {err_msg}\n原始输出: {raw_content}"
            )

        scene_count = len(outline.get("scene_outlines", []))
        print(f"[编剧] 大纲完成：{scene_count} 个场景")

        # ============================================================
        # 阶段4：作家写作
        # ============================================================
        writer_ctx = self.context_builder.build_writer_context(
            self.project_id, plan, outline
        )

        _stage("writer", f"[作家] 开始写作第 {chapter_num} 章...")
        full_text = self.writer.write_chapter(
            self.project_id,
            self.db,
            plan,
            on_token=on_token,
            context_override=writer_ctx,
        )
        print(f"\n[作家] 写作完成，字数：{len(full_text)}")

        # ============================================================
        # 阶段5：摘要生成
        # ============================================================
        _stage("summary", "[摘要] 生成章节摘要...")
        summary = self._generate_summary(full_text)

        # ============================================================
        # 阶段6：向量存储
        # ============================================================
        try:
            self.vector_store.add_chapter_summary(
                chapter_number=chapter_num,
                summary=summary,
                title=title,
            )
            print(f"[向量] 第{chapter_num}章摘要已写入向量库")
        except Exception as e:
            print(f"[警告] 向量写入失败（不影响生成）：{e}")

        # ============================================================
        # 阶段7：SQLite存储
        # ============================================================
        self.db.save_chapter(
            project_id=self.project_id,
            chapter_number=chapter_num,
            title=title,
            full_text=full_text,
            summary=summary,
            director_plan=json.dumps(plan, ensure_ascii=False),
            screenwriter_outline=json.dumps(outline, ensure_ascii=False),
        )

        self._update_foreshadowing(plan, chapter_num)

        result = {
            "chapter_number": chapter_num,
            "title": title,
            "full_text": full_text,
            "word_count": len(full_text),
            "summary": summary,
        }

        if on_paragraph_ready:
            on_paragraph_ready(full_text)

        return result

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    def _rewrite_previous_chapter(
        self,
        chapter_number: int,
        revision_notes: str,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """根据导演审查意见，调用作家模型重写指定章节"""
        chapter = self.db.get_chapter(self.project_id, chapter_number)
        project = self.db.get_project(self.project_id)
        original_text = chapter.full_text if chapter else ""

        # 获取前一章末尾用于衔接
        if chapter_number > 1:
            prev = self.db.get_chapter(self.project_id, chapter_number - 1)
            previous_tail = (prev.full_text or "")[-400:] if prev else ""
        else:
            previous_tail = "（本章为第一章，无上文）"

        system_content = (
            f"你是一位专业小说作家。你需要根据导演的修改意见重写一个章节。\n\n"
            f"小说题材：{project.genre or '未指定'}\n"
            f"叙事基调：{project.setting_tone or '自然流畅'}\n"
            f"目标字数：{self.config['generation'].get('chapter_target_words', 5000)}字\n\n"
            f"## 上章结尾\n{previous_tail}\n\n"
            f"## 导演修改意见\n{revision_notes}"
        )
        user_content = (
            f"## 原文\n{original_text[:5000]}\n\n"
            f"请根据导演的修改意见重写本章，直接输出正文，不要任何解释。"
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        if on_token:
            chunks = []
            for token in self.inference.call_agent_stream("writer", messages):
                chunks.append(token)
                on_token(token)
            return "".join(chunks)
        else:
            return self.inference.call_agent("writer", messages)

    def _generate_summary(self, full_text: str) -> str:
        """使用编剧模型生成章节摘要"""
        if not full_text or len(full_text.strip()) < 10:
            return "（本章正文内容缺失，无法生成摘要）"

        prompt_path = Path(__file__).parent.parent / "prompts" / "summarizer.txt"
        template = prompt_path.read_text(encoding="utf-8")
        prompt = template.replace("{full_text}", full_text[:3000])

        messages = [{"role": "user", "content": prompt}]
        try:
            summary = self.inference.call_agent("screenwriter", messages)
            return summary.strip()
        except Exception as e:
            print(f"[警告] 摘要生成失败：{e}")
            return f"（摘要生成失败）{full_text[:100]}..."

    def _update_foreshadowing(self, plan: dict, chapter_num: int) -> None:
        foreshadowing = plan.get("foreshadowing", {})
        if not isinstance(foreshadowing, dict):
            return
        for desc in foreshadowing.get("plant", []):
            if isinstance(desc, str) and desc.strip():
                self.db.add_foreshadowing(
                    project_id=self.project_id,
                    description=desc,
                    planted_chapter=chapter_num,
                )
        recall_list = foreshadowing.get("recall", [])
        if recall_list:
            pending = self.db.get_foreshadowing(self.project_id, status="planted")
            for recall_desc in recall_list:
                if not isinstance(recall_desc, str):
                    continue
                for f in pending:
                    if recall_desc.strip() in f.description or f.description in recall_desc.strip():
                        self.db.recall_foreshadowing(f.id, chapter_num)
                        break
