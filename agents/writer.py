"""
agents/writer.py
作家Agent：接收章节规划，生成小说正文（流式/非流式）
"""

import json
from typing import Callable, Iterator, Optional

from agents.base import BaseAgent
from memory.store import StoryDatabase


class WriterAgent(BaseAgent):
    def __init__(self, inference, language: str = "zh"):
        super().__init__(inference, "writer", "writer_system.txt", language)

    def write_chapter(
        self,
        project_id: str,
        db: StoryDatabase,
        plan: dict,
        on_token: Optional[Callable[[str], None]] = None,
        context_override: Optional[dict] = None,
    ) -> str:
        """
        根据导演规划写一整章正文。
        """
        context = context_override if context_override else self._build_context(project_id, db, plan)
        system_prompt = self._build_system_prompt(context)
        
        # 核心修复：将关键指令放在 User 消息中，利用近因效应防止”回显”大纲要求
        chapter_num = plan.get("chapter_number", 1)
        if self.language == "en":
            user_instruction = (
                f"Now, begin writing the full prose for chapter {chapter_num}.\n\n"
                "【MANDATORY INSTRUCTIONS】\n"
                "1. Output only novel prose. Never include any 'Requirements:', '1. 2. 3.', 'section headings', or task restatements.\n"
                "2. Maintain immersive narration. Do not write it as an essay or report. This is a professional long-form novel chapter.\n"
                "3. Absolutely never output irrelevant essay titles or anything unrelated to the project settings.\n"
                "4. Begin: output the first sentence directly.\n"
                "5. IMPORTANT: Your thinking process and the final output must be in English."
            )
        else:
            user_instruction = (
                f"现在，请开始创作第 {chapter_num} 章的正式小说正文。\n\n"
                "【强制执行指令】\n"
                "1. 只输出小说正文，严禁包含任何“要求：”、“1. 2. 3.”、“分段标题”或对任务的复述。\n"
                "2. 保持沉浸式叙事，禁止写成记叙文或作文。这是一部专业的长篇小说章节。\n"
                "3. 绝对禁止输出类似“我的第一份兼职”或任何与本项目设定无关的作文题目。\n"
                "4. 开始：直接输出第一句话。\n"
                "5. 重要：请使用中文进行思考和创作。"
            )

        messages = self._make_messages(system_prompt, user_instruction)

        if on_token:
            chunks = []
            for token in self.inference.call_agent_stream(self.role, messages):
                chunks.append(token)
                on_token(token)
            return "".join(chunks)
        else:
            return self.inference.call_agent(self.role, messages)

    # ------------------------------------------------------------------
    # 私有：组装上下文
    # ------------------------------------------------------------------

    def _build_context(self, project_id: str, db: StoryDatabase, plan: dict) -> dict:
        project = db.get_project(project_id)

        # 涉及角色（从key_scenes中提取）
        scene_char_names: set[str] = set()
        for scene in plan.get("key_scenes", []):
            for name in scene.get("characters", []):
                scene_char_names.add(name)

        characters = [
            db.get_character_by_name(project_id, name)
            for name in scene_char_names
        ]
        characters = [c for c in characters if c is not None]

        L = self.language
        character_profiles = _format_characters(characters, L)

        # 上文末尾800字
        previous_text = db.get_latest_chapter_text(project_id, char_count=800)
        if not previous_text:
            previous_text = (
                "(This is the first chapter, no preceding text)"
                if L == "en" else "（本章为第一章，无上文）"
            )

        # 风格样本块
        style_sample_block = ""
        if project.setting_style_sample:
            label = "Style Reference" if L == "en" else "风格参考"
            style_sample_block = f"## {label}\n{project.setting_style_sample}\n"

        # 场景摘要（给作家快速了解结构）
        key_scenes_summary = json.dumps(
            plan.get("key_scenes", []), ensure_ascii=False, indent=2
        )

        return {
            "style_description": project.setting_tone or (
                "Natural and fluid narrative style" if L == "en" else "自然流畅的叙事风格"
            ),
            "style_sample_block": style_sample_block,
            "narrative_goal": plan.get("narrative_goal",
                "Advance the story" if L == "en" else "推进故事发展"),
            "tone": plan.get("tone", ""),
            "key_scenes_summary": key_scenes_summary,
            "word_count_target": plan.get("word_count_target", 4000),
            "character_profiles": character_profiles,
            "previous_text": previous_text,
            "narrative_person": project.setting_narrative_person or (
                "third" if L == "en" else "第三"
            ),
        }


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

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


def _format_characters(characters: list, language: str = "zh") -> str:
    if not characters:
        return "No character information available." if language == "en" else "（无角色信息）"
    
    lines = []
    for c in characters:
        role = _translate_role(c.role, language)
        if language == "en":
            line = f"### {c.name} ({role})"
            if c.personality:
                line += f"\nPersonality: {c.personality}"
            if c.speech_style:
                line += f"\nSpeech Style: {c.speech_style}"
            if c.current_state:
                line += f"\nCurrent State: {c.current_state}"
        else:
            line = f"### {c.name}（{role}）"
            if c.personality:
                line += f"\n性格：{c.personality}"
            if c.speech_style:
                line += f"\n说话风格：{c.speech_style}"
            if c.current_state:
                line += f"\n当前状态：{c.current_state}"
        lines.append(line)
    return "\n\n".join(lines)
