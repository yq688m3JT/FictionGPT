"""
memory/context_builder.py
4层记忆上下文组装器：为Agent提供结构化的叙事上下文
"""

import json
from typing import Optional

from memory.store import StoryDatabase
from memory.vector_store import VectorStore


class ContextBuilder:
    """
    4层记忆架构：
    - Layer 1: 项目基础设定（世界观、题材、约束）
    - Layer 2: 最近N章摘要（保持叙事连贯性）
    - Layer 3: 角色当前状态（行为一致性）
    - Layer 4: ChromaDB语义检索（相关历史内容）
    """

    def __init__(self, db: StoryDatabase, vector_store: VectorStore, config: dict):
        self.db = db
        self.vs = vector_store
        self.recent_n = config["memory"].get("recent_chapters_count", 3)
        self.search_k = config["memory"].get("context_search_results", 5)

    def build_writer_context(
        self,
        project_id: str,
        plan: dict,
        outline: dict,
        include_vector: bool = True,
        language: str = "zh",
    ) -> dict:
        """
        为作家Agent组装完整上下文（4层）。
        """
        project = self.db.get_project(project_id)
        chapters = self.db.get_all_chapters(project_id)
        characters = self.db.get_all_characters(project_id)

        # Layer 1 — 项目设定
        layer1 = _format_project_settings_brief(project, language)

        # Layer 2 — 最近N章摘要
        recent = chapters[-self.recent_n:] if len(chapters) >= self.recent_n else chapters
        if recent:
            if language == "en":
                layer2 = "\n".join(
                    f"Ch.{c.chapter_number} \"{c.title}\": {c.summary or '(no summary)'}"
                    for c in recent
                )
            else:
                layer2 = "\n".join(
                    f"第{c.chapter_number}章《{c.title}》：{c.summary or '（无摘要）'}"
                    for c in recent
                )
        else:
            layer2 = "(No chapters yet)" if language == "en" else "（尚无章节）"

        # Layer 3 — 涉及角色状态
        scene_char_names: set[str] = set()
        for scene in plan.get("key_scenes", []):
            for name in scene.get("characters", []):
                scene_char_names.add(name)

        chars_in_scene = [c for c in characters if c.name in scene_char_names]
        all_chars = chars_in_scene if chars_in_scene else characters
        layer3 = _format_characters_detailed(all_chars, language)

        # Layer 4 — 向量检索（语义相关历史）
        layer4 = ""
        if include_vector and self.vs.collection.count() > 0:
            query = plan.get("narrative_goal", "")
            results = self.vs.search(query, n_results=self.search_k)
            if results:
                layer4 = self.vs.format_search_results(results)

        # 上文末尾（作家衔接用）
        previous_text = self.db.get_latest_chapter_text(project_id, char_count=800)
        if not previous_text:
            previous_text = (
                "(This is the first chapter, no preceding text)"
                if language == "en" else "（本章为第一章，无上文）"
            )

        # 风格样本块
        style_sample_block = ""
        if project.setting_style_sample:
            label = "Style Reference" if language == "en" else "风格参考"
            style_sample_block = f"## {label}\n{project.setting_style_sample}\n"

        # 编剧大纲（给作家的详细场景指导）
        outline_text = _format_outline(outline, language)

        # Layer 5 — 叙事解构摘要（全局叙事方向感知）
        arch = self.db.get_narrative_architecture(project_id)
        arch_context = ""
        if arch:
            arch_context = _format_architecture_brief(arch, plan.get("chapter_number", 0), language)

        return {
            "project_settings": layer1,
            "recent_summaries": layer2,
            "character_profiles": layer3,
            "vector_context": layer4,
            "architecture_context": arch_context,
            "previous_text": previous_text,
            "style_sample_block": style_sample_block,
            "narrative_goal": plan.get("narrative_goal",
                "Advance the story" if language == "en" else "推进故事发展"),
            "tone": plan.get("tone", ""),
            "word_count_target": plan.get("word_count_target", 4000),
            "narrative_person": project.setting_narrative_person or (
                "third" if language == "en" else "第三"
            ),
            "key_scenes_summary": outline_text,
            "style_description": project.setting_tone or (
                "Natural and fluid narrative style" if language == "en" else "自然流畅的叙事风格"
            ),
        }

    def build_director_context(self, project_id: str, language: str = "zh") -> dict:
        """为导演Agent组装上下文（Layer1+Layer2+Layer3）"""
        from agents.director import _format_project_settings

        project = self.db.get_project(project_id)
        chapters = self.db.get_all_chapters(project_id)
        characters = self.db.get_all_characters(project_id)
        pending_fs = self.db.get_foreshadowing(project_id, status="planted")

        recent = chapters[-5:] if len(chapters) >= 5 else chapters
        if language == "en":
            recent_summaries = "\n".join(
                f"Ch.{c.chapter_number} \"{c.title}\": {c.summary or '(no summary)'}"
                for c in recent
            ) or "(No chapters yet)"
        else:
            recent_summaries = "\n".join(
                f"第{c.chapter_number}章《{c.title}》：{c.summary or '（无摘要）'}"
                for c in recent
            ) or "（尚无章节）"

        if language == "en":
            pending_foreshadowing = "\n".join(
                f"- [{f.importance}] {f.description} (planted Ch.{f.planted_chapter})"
                for f in pending_fs
            ) or "(No unresolved foreshadowing)"
        else:
            pending_foreshadowing = "\n".join(
                f"- [{f.importance}] {f.description}（第{f.planted_chapter}章埋设）"
                for f in pending_fs
            ) or "（暂无未回收伏笔）"

        if language == "en":
            character_states = "\n".join(
                f"- {c.name} ({c.role}): {c.current_state or 'State unknown'}"
                for c in characters
            ) or "(No character information)"
        else:
            character_states = "\n".join(
                f"- {c.name}（{c.role}）：{c.current_state or '状态未知'}"
                for c in characters
            ) or "（暂无角色信息）"

        return {
            "project_settings": _format_project_settings(project, language),
            "chapter_count": len(chapters),
            "recent_summaries": recent_summaries,
            "pending_foreshadowing": pending_foreshadowing,
            "character_states": character_states,
            "constraints": project.setting_constraints or ("None" if language == "en" else "无"),
        }


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _format_project_settings_brief(project, language: str = "zh") -> str:
    if language == "en":
        return (
            f"Title: {project.title} | Genre: {project.genre or 'Not specified'} | "
            f"Tone: {project.setting_tone or 'Not specified'} | "
            f"Narrative: {project.setting_narrative_person or 'third'} person\n"
            f"Worldview: {project.setting_worldview or 'Not specified'}"
        )
    return (
        f"标题：{project.title} | 题材：{project.genre or '未指定'} | "
        f"基调：{project.setting_tone or '未指定'} | "
        f"叙事：{project.setting_narrative_person or '第三'}人称\n"
        f"世界观：{project.setting_worldview or '未指定'}"
    )


def _translate_role(role: str, language: str) -> str:
    if language != "en":
        return role
    mapping = {
        "主角": "Protagonist",
        "配角": "Supporting",
        "反派": "Antagonist",
        "龙套": "Extra",
    }
    return mapping.get(role, role)


def _format_characters_detailed(characters: list, language: str = "zh") -> str:
    if not characters:
        return "(No character information)" if language == "en" else "（无角色信息）"
    lines = []
    for c in characters:
        role = _translate_role(c.role, language)
        if language == "en":
            parts = [f"### {c.name} ({role})"]
            if c.personality:
                parts.append(f"Personality: {c.personality}")
            if c.speech_style:
                parts.append(f"Speech Style: {c.speech_style}")
            if c.background:
                parts.append(f"Background: {c.background}")
            if c.current_state:
                parts.append(f"Current State: {c.current_state}")
        else:
            parts = [f"### {c.name}（{role}）"]
            if c.personality:
                parts.append(f"性格：{c.personality}")
            if c.speech_style:
                parts.append(f"说话风格：{c.speech_style}")
            if c.background:
                parts.append(f"背景：{c.background}")
            if c.current_state:
                parts.append(f"当前状态：{c.current_state}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def _format_architecture_brief(arch: dict, current_chapter: int, language: str = "zh") -> str:
    """将叙事解构压缩为作家可感知的全局方向"""
    parts = []
    milestone = arch.get("milestone_chapter", "?")
    if language == "en":
        parts.append(f"Current narrative segment endpoint: Ch.{milestone} — {arch.get('milestone_description', '')}")
        parts.append(f"Segment Theme: {arch.get('narrative_theme', '')}")
    else:
        parts.append(f"当前叙事段落终点：第{milestone}章 — {arch.get('milestone_description', '')}")
        parts.append(f"本段主题：{arch.get('narrative_theme', '')}")

    story_lines = arch.get("story_lines", [])
    if story_lines:
        label = "Active Storylines" if language == "en" else "活跃故事线"
        parts.append(f"{label}：" + (" ; " if language == "en" else "；").join(
            f"{sl['name']}({sl['type']}): {sl.get('description', '')[:50]}"
            for sl in story_lines[:4]
        ))

    arcs = arch.get("character_arcs", {})
    if arcs:
        label = "Character Arc Directions" if language == "en" else "角色弧光方向"
        parts.append(f"{label}：" + (" ; " if language == "en" else "；").join(
            f"{name}: {info.get('starting_state', '')} → {info.get('ending_state', '')}"
            for name, info in list(arcs.items())[:4]
        ))

    return "\n".join(parts)


def _format_outline(outline: dict, language: str = "zh") -> str:
    """将编剧大纲格式化为作家可读的叙事性指导，避免列表格式导致报告感"""
    if not outline or "scene_outlines" not in outline:
        return (
            "(Please improvise based on narrative goals, maintaining plot continuity.)"
            if language == "en" else "（请根据叙事目标自由发挥，注意情节连贯。）"
        )

    parts = []

    opening = outline.get("opening_sentence_suggestion", "")
    if opening:
        label = "Opening Suggestion" if language == "en" else "开篇建议"
        parts.append(f"【{label}】：{opening}")

    pacing = outline.get("overall_pacing_note", "")
    if pacing:
        label = "Pacing Control" if language == "en" else "节奏调控"
        parts.append(f"【{label}】：{pacing}")

    for scene in outline.get("scene_outlines", []):
        sid = scene.get("scene_id", "?")
        if language == "en":
            parts.append(f"\n### Narrative Focus for Scene {sid}:")
        else:
            parts.append(f"\n### 关于场景 {sid} 的叙事重点：")

        if scene.get("opening_hook"):
            if language == "en":
                parts.append(f"This segment should open as follows: {scene['opening_hook']}")
            else:
                parts.append(f"本段应以这样一种方式切入：{scene['opening_hook']}")

        beats = scene.get("action_beats", [])
        if beats:
            if language == "en":
                parts.append("In this scene, you need to carefully depict the following plot developments:")
            else:
                parts.append("在此场景中，你需要细致刻画以下情节发展：")
            for beat in beats:
                parts.append(f"· {beat}")

        hints = scene.get("dialogue_hints", [])
        if hints:
            if language == "en":
                parts.append("Regarding dialogue interaction, consider the following directions:")
            else:
                parts.append("在对话交互方面，可以参考以下方向：")
            for h in hints:
                if language == "en":
                    parts.append(f"· {h.get('character', '?')} should exhibit: {h.get('hint', '')}")
                else:
                    parts.append(f"· {h.get('character', '?')} 应当表现出：{h.get('hint', '')}")

        if scene.get("emotional_turning_point"):
            if language == "en":
                parts.append(f"The core emotional turning point of this segment lies in: {scene['emotional_turning_point']}")
            else:
                parts.append(f"本段的情感转折核心在于：{scene['emotional_turning_point']}")

        if scene.get("closing_note"):
            if language == "en":
                parts.append(f"Finally, close in this manner to transition forward: {scene['closing_note']}")
            else:
                parts.append(f"最后，以如下方式收尾以衔接后续：{scene['closing_note']}")

    return "\n".join(parts)
