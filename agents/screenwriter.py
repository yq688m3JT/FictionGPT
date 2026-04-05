"""
agents/screenwriter.py
编剧Agent：将导演规划细化为详细场景大纲
"""

import json

from agents.base import BaseAgent
from agents.director import _format_project_settings, _safe_parse_json
from memory.store import StoryDatabase


class ScreenwriterAgent(BaseAgent):
    def __init__(self, inference, language: str = "zh"):
        super().__init__(inference, "screenwriter", "screenwriter_system.txt", language)

    def outline_chapter(self, project_id: str, db: StoryDatabase, plan: dict) -> dict:
        """
        基于导演规划生成详细场景大纲。
        返回 outline dict（包含 scene_outlines、pacing_note 等）。
        """
        context = self._build_context(project_id, db, plan)
        system_prompt = self._build_system_prompt(context)
        user_msg = (
            "Please detail the scene outline based on the director's plan. Output only JSON, nothing else. "
            "Your thinking process and output must be in English."
            if self.language == "en" else
            "请根据导演规划细化场景大纲。只输出JSON，不要任何其他内容。请使用中文进行思考和输出。"
        )
        messages = self._make_messages(system_prompt, user_msg)

        raw = self.inference.call_agent(self.role, messages)
        print(f"[Debug] Screenwriter raw output snippet: {raw[:200].replace(chr(10), ' ')}", flush=True)
        
        result = _safe_parse_json(raw)
        return result

    # ------------------------------------------------------------------

    def _build_context(self, project_id: str, db: StoryDatabase, plan: dict) -> dict:
        L = self.language
        project = db.get_project(project_id)
        characters = db.get_all_characters(project_id)

        character_states = "\n".join(
            f"- {c.name} ({c.role}): {c.current_state or 'State unknown'}"
            if L == "en" else f"- {c.name}（{c.role}）：{c.current_state or '状态未知'}"
            for c in characters
        ) or ("(No character information)" if L == "en" else "（暂无角色信息）")

        previous_text_tail = db.get_latest_chapter_text(project_id, char_count=300)
        if not previous_text_tail:
            previous_text_tail = (
                "(This is the first chapter, no preceding text)"
                if L == "en" else "（本章为第一章，无上文）"
            )

        return {
            "project_settings": _format_project_settings(project, L),
            "chapter_number": plan.get("chapter_number", "?"),
            "narrative_goal": plan.get("narrative_goal",
                "Advance the story" if L == "en" else "推进故事发展"),
            "tone": plan.get("tone", ""),
            "word_count_target": plan.get("word_count_target", 4000),
            "key_scenes_json": json.dumps(
                plan.get("key_scenes", []), ensure_ascii=False, indent=2
            ),
            "character_states": character_states,
            "previous_text_tail": previous_text_tail,
        }


# ------------------------------------------------------------------


def _fallback_outline(plan: dict, lang: str = "zh") -> dict:
    """编剧输出解析失败时的降级大纲"""
    scenes = plan.get("key_scenes", [])
    scene_outlines = []
    word_per_scene = plan.get("word_count_target", 4000) // max(len(scenes), 1)

    for scene in scenes:
        if lang == "en":
            scene_outlines.append({
                "scene_id": scene.get("scene_id", "1-1"),
                "opening_hook": f"Cut to {scene.get('location', 'scene')}",
                "action_beats": [scene.get("conflict", "Character faces conflict")],
                "dialogue_hints": [],
                "emotional_turning_point": scene.get("emotion_arc", "Emotional shift"),
                "closing_note": "Scene ends, transition to next scene",
            })
        else:
            scene_outlines.append({
                "scene_id": scene.get("scene_id", "1-1"),
                "opening_hook": f"镜头切入{scene.get('location', '场景')}",
                "action_beats": [scene.get("conflict", "角色面临冲突")],
                "dialogue_hints": [],
                "emotional_turning_point": scene.get("emotion_arc", "情感变化"),
                "closing_note": "场景结束，切入下一场景",
            })

    return {
        "scene_outlines": scene_outlines,
        "overall_pacing_note": "Steady progression" if lang == "en" else "稳步推进",
        "opening_sentence_suggestion": "",
        "word_allocation": {
            s.get("scene_id", f"scene_{i}"): word_per_scene
            for i, s in enumerate(scenes)
        },
    }
